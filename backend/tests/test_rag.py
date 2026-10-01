"""Kiểm thử Module B: RAG với tài liệu thật, trích dẫn nguồn và chống ảo giác."""

from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app.repositories import citations as citations_repo
from app.repositories import documents as documents_repo
from app.services import documents as documents_service
from app.services import vector_store

from .conftest import auth_header
from .test_chat import FakeProvider, use_provider

DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Câu hỏi và nội dung tài liệu cùng dùng từ khoá "gradient" để vector giả khớp nhau.
QUESTION = "Gradient descent hoat dong the nao?"


def _upload_knowledge(client: TestClient, token: str, docx_factory) -> int:
    """Tải lên tài liệu có nội dung liên quan và chờ tới trạng thái ready."""
    content = docx_factory("Giáo trình Trí tuệ nhân tạo", paragraphs=6)
    response = client.post(
        "/api/documents",
        files={"file": ("bai-giang.docx", content, DOCX_CONTENT_TYPE)},
        headers=auth_header(token),
    )
    assert response.status_code == 201, response.text
    document_id = response.json()["id"]
    status = client.get(f"/api/documents/{document_id}/status", headers=auth_header(token)).json()
    assert status["status"] == "ready", status
    return document_id


def test_upload_creates_vector_file_and_refs(client: TestClient, make_user, docx_factory) -> None:
    """Tài liệu ready phải có tệp vector và chunk đã được gắn vector_ref."""
    token, user_id = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    assert vector_store.vector_path(user_id, document_id).exists()

    chunks = client.get(f"/api/documents/{document_id}/chunks", headers=auth_header(token)).json()
    assert chunks["total"] >= 1
    assert all(item["vector_ref"] for item in chunks["items"])


def test_chat_with_context_returns_citations(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Có ngữ cảnh thì LLM nhận prompt RAG và câu trả lời kèm nguồn trích dẫn."""
    provider = FakeProvider(content="Gradient descent giảm dần theo hướng đạo hàm âm [1].")
    use_provider(monkeypatch, provider)
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    response = client.post(
        "/api/chat",
        json={"message": QUESTION, "document_id": document_id},
        headers=auth_header(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["citations"], body
    first = body["citations"][0]
    assert first["document_id"] == document_id
    assert first["file_name"] == "bai-giang.docx"
    assert first["snippet"]

    # Prompt phải là bản RAG và có kèm khối ngữ cảnh.
    sent = provider.calls[-1][0]
    assert "NGỮ CẢNH TỪ TÀI LIỆU" in sent[-1]["content"]
    assert "DỰA TRÊN CHÍNH CÁC TRÍCH ĐOẠN" in sent[0]["content"]


def test_chat_saves_citations_to_database(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Nguồn trích dẫn phải được lưu lại để tra cứu về sau."""
    use_provider(monkeypatch, FakeProvider(content="Có ngữ cảnh [1]."))
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    body = client.post(
        "/api/chat",
        json={"message": QUESTION, "document_id": document_id},
        headers=auth_header(token),
    ).json()

    from app.db import read_connection

    with read_connection() as connection:
        row = connection.execute(
            "SELECT id FROM messages WHERE conversation_id = ? AND role = 'assistant' ORDER BY id DESC LIMIT 1",
            (body["conversation_id"],),
        ).fetchone()
    saved = citations_repo.list_for_message(int(row["id"]))
    assert saved
    assert saved[0]["document_id"] == document_id
    assert saved[0]["file_name"] == "bai-giang.docx"


def test_chat_without_relevant_context_refuses_to_guess(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Có tài liệu nhưng câu hỏi không liên quan thì phải nói chưa đủ thông tin (NFR-4)."""
    provider = FakeProvider(content="Câu trả lời bịa đặt")
    use_provider(monkeypatch, provider)
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    body = client.post(
        "/api/chat",
        json={"message": "chu de hoac toan khong lien quan gi", "document_id": document_id},
        headers=auth_header(token),
    ).json()

    assert body["citations"] == []
    assert "chưa tìm thấy" in body["answer"]
    assert provider.calls == [], "không được gọi LLM khi không có ngữ cảnh"


def test_chat_without_documents_still_answers(
    client: TestClient, monkeypatch, make_user
) -> None:
    """Chưa tải tài liệu nào thì vẫn trò chuyện bình thường với LLM."""
    provider = FakeProvider(content="Đây là câu trả lời chung về Gradient descent.")
    use_provider(monkeypatch, provider)
    token, _ = make_user()

    body = client.post("/api/chat", json={"message": QUESTION}, headers=auth_header(token)).json()

    assert body["answer"].startswith("Đây là câu trả lời")
    assert body["citations"] == []
    assert provider.calls, "phải gọi LLM khi người dùng chưa có tài liệu"


def test_chat_still_answers_general_question_when_documents_exist(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Đã có tài liệu, nhưng hỏi câu chung (không chọn tài liệu) thì AI vẫn phải trả lời.

    Đây là lỗi cần tránh: chỉ cần người dùng tải lên một tài liệu là trợ lý từ chối
    mọi câu hỏi thông thường vì không tìm thấy ngữ cảnh.
    """
    provider = FakeProvider(content="Đây là câu trả lời chung cho câu hỏi thông thường.")
    use_provider(monkeypatch, provider)
    token, _ = make_user()
    _upload_knowledge(client, token, docx_factory)  # người dùng đã có tài liệu ready

    body = client.post(
        "/api/chat",
        json={"message": "Thủ đô của nước ta tên là gì"},
        headers=auth_header(token),
    ).json()

    assert body["answer"].startswith("Đây là câu trả lời chung")
    assert body["used_documents"] is False
    assert body["citations"] == []
    assert provider.calls, "phải gọi LLM cho câu hỏi không liên quan tới tài liệu"


def test_chat_marks_used_documents_when_context_found(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Khi câu trả lời dựa trên tài liệu thì cờ used_documents phải bật."""
    use_provider(monkeypatch, FakeProvider(content="Theo tài liệu [1]."))
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    body = client.post(
        "/api/chat",
        json={"message": QUESTION, "document_id": document_id},
        headers=auth_header(token),
    ).json()

    assert body["used_documents"] is True
    assert body["citations"]


def test_chat_rejects_document_of_another_user(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    """Không hỏi được trên tài liệu của người khác (NFR-3)."""
    use_provider(monkeypatch, FakeProvider())
    owner_token, _ = make_user()
    document_id = _upload_knowledge(client, owner_token, docx_factory)
    other_token, _ = make_user()

    response = client.post(
        "/api/chat",
        json={"message": QUESTION, "document_id": document_id},
        headers=auth_header(other_token),
    )
    assert response.status_code == 404


def test_delete_document_removes_vector_file(
    client: TestClient, make_user, docx_factory
) -> None:
    """Xoá tài liệu phải xoá luôn tệp vector, nếu không sẽ tìm nhầm dữ liệu cũ."""
    token, user_id = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)
    path = vector_store.vector_path(user_id, document_id)
    assert path.exists()

    assert client.delete(f"/api/documents/{document_id}", headers=auth_header(token)).status_code == 200
    assert not path.exists()
    assert documents_repo.get_by_id(document_id) is None


def test_regenerated_vectors_replace_old_file(client: TestClient, make_user, docx_factory) -> None:
    """Sinh lại vector phải ghi đè, không nối thêm làm dư."""
    from app.db import transaction

    token, user_id = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)
    path = vector_store.vector_path(user_id, document_id)
    size_before = path.stat().st_size

    # Xoá vector_ref để buộc sinh lại toàn bộ.
    with transaction() as connection:
        connection.execute("UPDATE chunks SET vector_ref = NULL WHERE document_id = ?", (document_id,))

    assert asyncio.run(documents_service.embed_document(document_id)) > 0
    assert path.stat().st_size == size_before
