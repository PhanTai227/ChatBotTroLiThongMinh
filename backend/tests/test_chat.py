"""Kiểm thử endpoint trợ lý AI, dùng nhà cung cấp LLM giả lập."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.routers import chat as chat_router
from app.services.llm import (
    LLMEmptyResponse,
    LLMModelMissing,
    LLMResult,
    LLMTimeout,
    LLMUnavailable,
)

from .conftest import auth_header


class FakeProvider:
    """Nhà cung cấp AI giả lập để kiểm thử không phụ thuộc Ollama thật."""

    name = "fake"

    def __init__(self, content: str = "Đây là câu trả lời thử nghiệm.", error: Exception | None = None):
        self.content = content
        self.error = error
        self.calls: list[tuple[list[dict[str, str]], str]] = []

    async def generate(self, messages: list[dict[str, str]], model: str) -> LLMResult:
        self.calls.append((messages, model))
        if self.error is not None:
            raise self.error
        return LLMResult(content=self.content, model=model)

    async def stream(self, messages: list[dict[str, str]], model: str):
        """Bản streaming của cùng nội dung, chia nhỏ để kiểm tra nối delta."""
        self.calls.append((messages, model))
        if self.error is not None:
            raise self.error
        # Chia thành 3 mốc để kiểm tra bên nhận được nhiều sự kiện delta.
        step = max(1, len(self.content) // 3)
        for start in range(0, len(self.content), step):
            yield self.content[start : start + step]

    async def list_models(self) -> list[str]:
        if self.error is not None:
            raise self.error
        return ["qwen2.5:3b"]

    async def version(self) -> str:
        return "test"


async def _fake_model() -> str:
    return "qwen2.5:3b"


def use_provider(monkeypatch: pytest.MonkeyPatch, provider: FakeProvider, *, patch_model: bool = True) -> None:
    """Gắn nhà cung cấp AI giả lập. patch_model=False để kiểm tra việc chọn model thật."""
    monkeypatch.setattr(chat_router, "get_provider", lambda: provider)
    if patch_model:
        monkeypatch.setattr(chat_router, "resolve_model", _fake_model)


def test_chat_requires_authentication(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    use_provider(monkeypatch, FakeProvider())
    assert client.post("/api/chat", json={"message": "Xin chào"}).status_code == 401


def test_chat_stores_question_and_answer(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    provider = FakeProvider(content="Gradient Descent từng bước: tính gradient, cập nhật tham số.")
    use_provider(monkeypatch, provider)
    token, _ = make_user()

    response = client.post(
        "/api/chat",
        json={"message": "Gradient Descent hoạt động thế nào?"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"].startswith("Gradient Descent")
    assert body["model"] == "qwen2.5:3b"
    assert body["conversation_id"] > 0

    from app.db import read_connection

    with read_connection() as connection:
        messages = connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id", (body["conversation_id"],)
        ).fetchall()
    assert [row["role"] for row in messages] == ["user", "assistant"]
    # Câu hỏi phải được gửi kèm chỉ dẫn hệ thống tiếng Việt.
    assert provider.calls[0][0][0]["role"] == "system"


def test_chat_reuses_same_conversation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    use_provider(monkeypatch, FakeProvider())
    token, _ = make_user()
    first = client.post("/api/chat", json={"message": "Câu hỏi một"}, headers=auth_header(token)).json()
    second = client.post(
        "/api/chat",
        json={"message": "Câu hỏi hai", "conversation_id": first["conversation_id"]},
        headers=auth_header(token),
    ).json()
    assert second["conversation_id"] == first["conversation_id"]


def test_chat_cannot_use_conversation_of_another_user(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    use_provider(monkeypatch, FakeProvider())
    first_token, _ = make_user()
    conversation = client.post(
        "/api/chat", json={"message": "Hội thoại riêng"}, headers=auth_header(first_token)
    ).json()["conversation_id"]
    second_token, _ = make_user()

    response = client.post(
        "/api/chat",
        json={"message": "Cố xem hội thoại người khác", "conversation_id": conversation},
        headers=auth_header(second_token),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (LLMTimeout("slow"), 504, "ai_timeout"),
        (LLMUnavailable("down"), 503, "ai_unavailable"),
        (LLMModelMissing("missing"), 503, "ai_unavailable"),
        (LLMEmptyResponse("empty"), 502, "ai_bad_gateway"),
    ],
)
def test_chat_maps_ai_errors(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    make_user,
    error: Exception,
    expected_status: int,
    expected_code: str,
) -> None:
    use_provider(monkeypatch, FakeProvider(error=error))
    token, _ = make_user()
    response = client.post("/api/chat", json={"message": "Câu hỏi khi AI lỗi"}, headers=auth_header(token))
    assert response.status_code == expected_status
    assert response.json()["code"] == expected_code


def test_question_is_kept_even_when_ai_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    use_provider(monkeypatch, FakeProvider(error=LLMUnavailable("down")))
    token, _ = make_user()
    client.post("/api/chat", json={"message": "Câu hỏi phải được lưu"}, headers=auth_header(token))

    from app.db import read_connection

    with read_connection() as connection:
        row = connection.execute(
            "SELECT role, content FROM messages WHERE role = 'user' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row["content"] == "Câu hỏi phải được lưu"


def test_empty_message_is_rejected(client: TestClient, make_user) -> None:
    token, _ = make_user()
    assert client.post("/api/chat", json={"message": "   "}, headers=auth_header(token)).status_code == 422


def test_chat_stream_emits_deltas_and_done(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    """Streaming trả về meta -> nhiều delta -> citations -> done, và lưu đủ tin nhắn."""
    provider = FakeProvider(content="Gradient Descent từng bước: tính gradient, cập nhật tham số.")
    use_provider(monkeypatch, provider)
    token, _ = make_user()

    response = client.post(
        "/api/chat/stream",
        json={"message": "Gradient Descent hoạt động thế nào?"},
        headers=auth_header(token),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    import json as jsonlib

    events = [
        jsonlib.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[0]["type"] == "meta"
    assert events[0]["conversation_id"] > 0
    deltas = [event for event in events if event["type"] == "delta"]
    assert len(deltas) >= 2  # nội dung bị chia thành nhiều phần
    assert "".join(event["text"] for event in deltas) == provider.content
    assert events[-1]["type"] == "done"
    assert any(event["type"] == "citations" for event in events)

    from app.db import read_connection

    with read_connection() as connection:
        messages = connection.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id",
            (events[0]["conversation_id"],),
        ).fetchall()
    assert [row["role"] for row in messages] == ["user", "assistant"]
    assert messages[1]["content"] == provider.content


def test_chat_stream_reports_ai_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    """Lỗi AI giữa chừng được báo qua sự kiện error thay vì sập kết nối."""
    use_provider(monkeypatch, FakeProvider(error=LLMUnavailable("down")))
    token, _ = make_user()

    response = client.post(
        "/api/chat/stream", json={"message": "Câu hỏi khi AI lỗi"}, headers=auth_header(token)
    )
    assert response.status_code == 200
    assert '"type": "error"' in response.text or '"type":"error"' in response.text.replace(" ", "")


def test_chat_uses_conversation_history_in_prompt(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, make_user
) -> None:
    """Các lượt hỏi trước phải được đưa vào prompt để AI hiểu ngữ cảnh nhiều lượt."""
    provider = FakeProvider()
    use_provider(monkeypatch, provider)
    token, _ = make_user()
    first = client.post(
        "/api/chat", json={"message": "Giải thích về RAG"}, headers=auth_header(token)
    ).json()
    client.post(
        "/api/chat",
        json={"message": "Vậy nó khác gì fine-tuning?", "conversation_id": first["conversation_id"]},
        headers=auth_header(token),
    )

    second_call_messages = provider.calls[-1][0]
    roles = [message["role"] for message in second_call_messages]
    contents = [message["content"] for message in second_call_messages]
    assert roles[0] == "system"
    # Có đủ: system + user(lượt 1) + assistant(trả lời 1) + user(câu 2).
    assert "Giải thích về RAG" in contents
    assert any(role == "assistant" for role in roles[1:-1])
    assert contents[-1].endswith("Vậy nó khác gì fine-tuning?")
