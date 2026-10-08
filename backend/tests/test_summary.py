"""Kiểm thử Module C: tóm tắt tài liệu theo yêu cầu (FR-B5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services import summaries as summaries_service
from app.services.llm import LLMUnavailable

from .conftest import auth_header
from .test_chat import FakeProvider
from .test_rag import _upload_knowledge


class SummaryProvider(FakeProvider):
    """Nhà cung cấp LLM giả tương thích chữ ký `num_predict` của dịch vụ tóm tắt."""

    async def generate(self, messages: list[dict[str, str]], model: str, *, num_predict: int | None = None):
        return await super().generate(messages, model)


def _blank_document(client: TestClient, token: str, upload) -> int:
    """Tài liệu lỗi (trang trắng) để kiểm tra trạng thái 'chưa sẵn sàng'."""
    import fitz

    blank = fitz.open()
    blank.new_page()
    payload = blank.tobytes()
    blank.close()
    return int(upload(token, payload, filename="trang-trang.pdf").json()["id"])


def use_summary_provider(monkeypatch, provider: SummaryProvider) -> SummaryProvider:
    async def _model() -> str:
        return "qwen2.5:3b"

    monkeypatch.setattr(summaries_service, "get_provider", lambda: provider)
    monkeypatch.setattr(summaries_service, "resolve_model", _model)
    return provider


def test_summary_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/documents/1/summary").status_code == 401


def test_summary_generated_once_then_cached(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    provider = use_summary_provider(
        monkeypatch, SummaryProvider(content="- Gradient Descent la thuat toan toi uu\n- Nguoc huong gradient")
    )
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    first = client.get(f"/api/documents/{document_id}/summary", headers=auth_header(token))
    assert first.status_code == 200, first.text
    assert first.json()["cached"] is False
    assert first.json()["content"].startswith("- Gradient Descent")

    second = client.get(f"/api/documents/{document_id}/summary", headers=auth_header(token))
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert len(provider.calls) == 1  # lan thu hai dung ban luu, khong goi LLM lai


def test_summary_requires_ready_document(
    client: TestClient, monkeypatch, make_user, upload
) -> None:
    use_summary_provider(monkeypatch, SummaryProvider(content="- Khong nen thay noi dung nay"))
    token, _ = make_user()
    document_id = _blank_document(client, token, upload)

    response = client.get(f"/api/documents/{document_id}/summary", headers=auth_header(token))
    assert response.status_code == 409


def test_summary_of_another_user_is_not_found(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    use_summary_provider(monkeypatch, SummaryProvider(content="- Noi dung rieng tu"))
    owner_token, _ = make_user()
    document_id = _upload_knowledge(client, owner_token, docx_factory)
    other_token, _ = make_user()

    response = client.get(f"/api/documents/{document_id}/summary", headers=auth_header(other_token))
    assert response.status_code == 404


def test_summary_maps_ai_error(
    client: TestClient, monkeypatch, make_user, docx_factory
) -> None:
    use_summary_provider(monkeypatch, SummaryProvider(error=LLMUnavailable("down")))
    token, _ = make_user()
    document_id = _upload_knowledge(client, token, docx_factory)

    response = client.get(f"/api/documents/{document_id}/summary", headers=auth_header(token))
    assert response.status_code == 503
    assert response.json()["code"] == "ai_unavailable"
