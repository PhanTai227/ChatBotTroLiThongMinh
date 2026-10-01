"""Kiểm thử Module A: tải tài liệu lên, xử lý nền và quản lý tài liệu."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import read_connection
from app.repositories import chunks as chunks_repo
from app.repositories import jobs as jobs_repo
from app.repositories import settings_repo
from app.services import storage

from .conftest import auth_header

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_upload_pdf_becomes_ready_with_chunks(
    client: TestClient, make_user, upload, sample_pdf: bytes
) -> None:
    token, _ = make_user()
    response = upload(token, sample_pdf, filename="bai-giang.pdf", subject_tag="Tri tue nhan tao")
    assert response.status_code == 201, response.text
    document = response.json()
    document_id = document["id"]
    assert document["subject_tag"] == "Tri tue nhan tao"
    assert document["file_type"] == "pdf"

    # Việc xử lý chạy nền ngay sau khi trả kết quả nên tài liệu đã sẵn sàng.
    body = client.get(f"/api/documents/{document_id}/status", headers=auth_header(token)).json()
    assert body["status"] == "ready", body
    assert body["chunk_count"] >= 1
    assert body["page_count"] == 2
    assert body["extract_method"] == "text"


def test_upload_docx_extracts_vietnamese_text(
    client: TestClient, make_user, upload, sample_docx: bytes
) -> None:
    token, _ = make_user()
    response = upload(token, sample_docx, filename="giao-trinh.docx", content_type=DOCX_CONTENT_TYPE)
    assert response.status_code == 201
    document_id = response.json()["id"]

    chunks = client.get(f"/api/documents/{document_id}/chunks", headers=auth_header(token)).json()
    assert chunks["total"] >= 1
    assert "Gradient" in " ".join(item["content"] for item in chunks["items"])


def test_upload_rejects_unsupported_extension(client: TestClient, make_user, upload) -> None:
    token, _ = make_user()
    response = upload(token, b"plain text", filename="ghi-chu.txt", content_type="text/plain")
    assert response.status_code == 415
    assert response.json()["code"] == "unsupported_media_type"


def test_upload_rejects_fake_pdf(client: TestClient, make_user, upload) -> None:
    token, _ = make_user()
    assert upload(token, b"day khong phai PDF", filename="gia-mao.pdf").status_code == 415


def test_upload_rejects_empty_file(client: TestClient, make_user, upload) -> None:
    token, _ = make_user()
    assert upload(token, b"", filename="rong.pdf").status_code == 415


def test_upload_rejects_oversized_file(
    client: TestClient, make_user, upload, sample_pdf: bytes
) -> None:
    token, _ = make_user()
    original = settings_repo.get_value("max_upload_mb")
    settings_repo.set_value("max_upload_mb", "1")
    try:
        response = upload(token, sample_pdf + b"\x00" * (2 * 1024 * 1024), filename="lon.pdf")
        assert response.status_code == 413
        assert response.json()["code"] == "payload_too_large"
    finally:
        settings_repo.set_value("max_upload_mb", original or "20")


def test_duplicate_upload_is_rejected(client: TestClient, make_user, upload, sample_pdf: bytes) -> None:
    token, _ = make_user()
    first = upload(token, sample_pdf, filename="bai-giang.pdf")
    assert first.status_code == 201
    second = upload(token, sample_pdf, filename="bai-giang-copy.pdf")
    assert second.status_code == 409
    assert str(first.json()["id"]) in second.json()["detail"]


def test_other_user_cannot_see_or_delete(client: TestClient, make_user, upload, sample_pdf: bytes) -> None:
    owner_token, _ = make_user()
    document_id = upload(owner_token, sample_pdf, filename="rieng-tu.pdf").json()["id"]
    other_token, _ = make_user()

    assert client.get(f"/api/documents/{document_id}", headers=auth_header(other_token)).status_code == 404
    assert client.delete(f"/api/documents/{document_id}", headers=auth_header(other_token)).status_code == 404
    assert client.get("/api/documents", headers=auth_header(other_token)).json()["total"] == 0


def test_upload_requires_authentication(client: TestClient, sample_pdf: bytes) -> None:
    response = client.post("/api/documents", files={"file": ("a.pdf", sample_pdf, "application/pdf")})
    assert response.status_code == 401


def test_list_documents_supports_search_and_pagination(
    client: TestClient, make_user, upload, docx_factory
) -> None:
    token, _ = make_user()
    upload(token, docx_factory("Mon toan"), filename="mon-toan.docx", content_type=DOCX_CONTENT_TYPE)
    upload(token, docx_factory("Mon ly"), filename="mon-ly.docx", content_type=DOCX_CONTENT_TYPE)

    assert client.get("/api/documents", headers=auth_header(token)).json()["total"] == 2

    filtered = client.get("/api/documents?q=mon-toan", headers=auth_header(token)).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["file_name"] == "mon-toan.docx"

    page = client.get("/api/documents?limit=1&offset=1", headers=auth_header(token)).json()
    assert len(page["items"]) == 1


def test_update_metadata(client: TestClient, make_user, upload, sample_pdf: bytes) -> None:
    token, _ = make_user()
    document_id = upload(token, sample_pdf, filename="cu.pdf").json()["id"]
    response = client.patch(
        f"/api/documents/{document_id}",
        json={"file_name": "tai-lieu-ai.pdf", "subject_tag": "AI", "chapter_tag": "Chuong 1"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["file_name"] == "tai-lieu-ai.pdf"
    assert body["subject_tag"] == "AI"
    assert body["chapter_tag"] == "Chuong 1"


def test_delete_document_removes_file_and_chunks(
    client: TestClient, make_user, upload, sample_pdf: bytes
) -> None:
    token, _ = make_user()
    document = upload(token, sample_pdf, filename="xoa.pdf").json()
    path = storage.resolve_stored_path(document["storage_path"])
    assert path.exists()

    assert client.delete(f"/api/documents/{document['id']}", headers=auth_header(token)).status_code == 200
    assert not path.exists()
    with read_connection() as connection:
        remaining = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document["id"],)
        ).fetchone()[0]
    assert int(remaining) == 0


def test_failed_processing_marks_document_error(
    client: TestClient, make_user, upload, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tệp hỏng phải đưa tài liệu về trạng thái lỗi kèm thông báo, không làm sập tiến trình."""
    from app.services import extraction

    def boom(_path, _file_type):
        raise extraction.ExtractionError("Tệp PDF không hợp lệ.")

    monkeypatch.setattr(extraction, "extract", boom)
    token, _ = make_user()
    document_id = upload(token, b"%PDF-1.4 broken", filename="hong.pdf").json()["id"]
    body = client.get(f"/api/documents/{document_id}/status", headers=auth_header(token)).json()
    assert body["status"] == "error"
    assert "không hợp lệ" in body["error_message"]


def test_empty_text_marks_document_error(client: TestClient, make_user, upload) -> None:
    """Tệp không có chữ (ví dụ trang trắng) phải báo lỗi rõ ràng chứ không tạo tài liệu rỗng."""
    import fitz

    blank = fitz.open()
    blank.new_page()
    payload = blank.tobytes()
    blank.close()

    token, _ = make_user()
    document_id = upload(token, payload, filename="trang-trang.pdf").json()["id"]
    body = client.get(f"/api/documents/{document_id}/status", headers=auth_header(token)).json()
    assert body["status"] == "error"
    assert chunks_repo.count_for_document(document_id) == 0


def test_job_queue_claim_and_retry(client: TestClient, make_user, upload, sample_pdf: bytes) -> None:
    token, _ = make_user()
    document_id = int(upload(token, sample_pdf, filename="hang-cho.pdf").json()["id"])

    job_id = jobs_repo.enqueue(document_id, jobs_repo.STAGE_OCR)
    claimed = jobs_repo.claim_next(jobs_repo.STAGE_OCR)
    assert claimed is not None
    assert int(claimed["id"]) == job_id
    assert int(claimed["document_id"]) == document_id
    assert int(claimed["attempts"]) == 1
    assert jobs_repo.claim_next(jobs_repo.STAGE_OCR) is None  # không nhận trùng việc đang chạy
    before = jobs_repo.stats().get("done", 0)
    jobs_repo.mark_done(job_id)
    assert jobs_repo.stats().get("done", 0) == before + 1


def test_storage_rejects_path_traversal() -> None:
    with pytest.raises(storage.StorageError):
        storage.resolve_stored_path("../../../Windows/System32/config/SAM")


def test_storage_dir_exists() -> None:
    assert get_settings().storage_dir.exists()
