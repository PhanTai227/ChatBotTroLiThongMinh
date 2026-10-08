"""Kiểm thử endpoint hội thoại: danh sách, đọc tin nhắn và xoá (FR-B6, FR-C5)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import auth_header
from .test_chat import FakeProvider, use_provider


def test_conversations_require_authentication(client: TestClient) -> None:
    assert client.get("/api/conversations").status_code == 401
    assert client.delete("/api/conversations/1").status_code == 401


def test_chat_creates_conversation_visible_in_list(
    client: TestClient, monkeypatch, make_user
) -> None:
    use_provider(monkeypatch, FakeProvider())
    token, _ = make_user()
    conversation_id = client.post(
        "/api/chat", json={"message": "Câu hỏi đầu tiên"}, headers=auth_header(token)
    ).json()["conversation_id"]

    listed = client.get("/api/conversations", headers=auth_header(token))
    assert listed.status_code == 200
    items = listed.json()["items"]
    match = next(item for item in items if item["id"] == conversation_id)
    assert match["title"] == "Câu hỏi đầu tiên"
    assert match["message_count"] == 2  # user + assistant

    detail = client.get(f"/api/conversations/{conversation_id}", headers=auth_header(token))
    assert detail.status_code == 200
    body = detail.json()
    assert [message["role"] for message in body["messages"]] == ["user", "assistant"]


def test_cannot_read_conversation_of_another_user(
    client: TestClient, monkeypatch, make_user
) -> None:
    use_provider(monkeypatch, FakeProvider())
    first_token, _ = make_user()
    conversation_id = client.post(
        "/api/chat", json={"message": "Riêng tư"}, headers=auth_header(first_token)
    ).json()["conversation_id"]
    second_token, _ = make_user()

    response = client.get(
        f"/api/conversations/{conversation_id}", headers=auth_header(second_token)
    )
    assert response.status_code == 404


def test_delete_conversation_removes_it(client: TestClient, monkeypatch, make_user) -> None:
    use_provider(monkeypatch, FakeProvider())
    token, _ = make_user()
    conversation_id = client.post(
        "/api/chat", json={"message": "Sắp xoá"}, headers=auth_header(token)
    ).json()["conversation_id"]

    deleted = client.delete(f"/api/conversations/{conversation_id}", headers=auth_header(token))
    assert deleted.status_code == 200
    assert client.get(f"/api/conversations/{conversation_id}", headers=auth_header(token)).status_code == 404
    # Xoá lần nữa phải báo không tìm thấy, không im lặng thành công.
    assert client.delete(f"/api/conversations/{conversation_id}", headers=auth_header(token)).status_code == 404
    listed = client.get("/api/conversations", headers=auth_header(token)).json()["items"]
    assert all(item["id"] != conversation_id for item in listed)
