"""Kiểm thử nhóm quản trị và phân quyền."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import auth_header


def test_regular_user_cannot_open_admin(client: TestClient, make_user) -> None:
    token, _ = make_user()
    response = client.get("/api/admin/users", headers=auth_header(token))
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


def test_admin_lists_users(client: TestClient, admin_token: str, make_user) -> None:
    make_user()
    response = client.get("/api/admin/users", headers=auth_header(admin_token))
    assert response.status_code == 200
    emails = [user["email"] for user in response.json()]
    assert "admin@mindora.local" in emails


def test_admin_cannot_demote_self(client: TestClient, admin_token: str) -> None:
    me = client.get("/api/auth/me", headers=auth_header(admin_token)).json()["user"]
    response = client.patch(
        "/api/admin/users", json={"user_id": me["id"], "role": "user"}, headers=auth_header(admin_token)
    )
    assert response.status_code == 400


def test_admin_cannot_lock_self(client: TestClient, admin_token: str) -> None:
    me = client.get("/api/auth/me", headers=auth_header(admin_token)).json()["user"]
    response = client.patch(
        "/api/admin/users", json={"user_id": me["id"], "is_active": False}, headers=auth_header(admin_token)
    )
    assert response.status_code == 400


def test_admin_cannot_delete_self(client: TestClient, admin_token: str) -> None:
    me = client.get("/api/auth/me", headers=auth_header(admin_token)).json()["user"]
    assert client.delete(f"/api/admin/users/{me['id']}", headers=auth_header(admin_token)).status_code == 400


def test_password_change_revokes_sessions(client: TestClient, admin_token: str, make_user) -> None:
    token, user_id = make_user(email="doi.mat.khau@mindora.test", password="HocTap@123")
    patched = client.patch(
        "/api/admin/users",
        json={"user_id": user_id, "new_password": "MatKhauMoi@1"},
        headers=auth_header(admin_token),
    )
    assert patched.status_code == 200
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401
    assert (
        client.post(
            "/api/auth/login", json={"email": "doi.mat.khau@mindora.test", "password": "MatKhauMoi@1"}
        ).status_code
        == 200
    )


def test_delete_user_cascades_sessions(client: TestClient, admin_token: str, make_user) -> None:
    token, user_id = make_user(email="bi.xoa@mindora.test")
    assert client.delete(f"/api/admin/users/{user_id}", headers=auth_header(admin_token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401
    assert client.delete(f"/api/admin/users/{user_id}", headers=auth_header(admin_token)).status_code == 404


def test_settings_read_and_update(client: TestClient, admin_token: str) -> None:
    listed = client.get("/api/admin/settings", headers=auth_header(admin_token))
    assert listed.status_code == 200
    keys = {item["key"] for item in listed.json()}
    assert {"max_upload_mb", "ai_model"} <= keys

    updated = client.patch(
        "/api/admin/settings/max_upload_mb", json={"value": "35"}, headers=auth_header(admin_token)
    )
    assert updated.status_code == 200
    after = client.get("/api/admin/settings", headers=auth_header(admin_token)).json()
    assert next(item for item in after if item["key"] == "max_upload_mb")["value"] == "35"


def test_update_unknown_setting_returns_404(client: TestClient, admin_token: str) -> None:
    response = client.patch(
        "/api/admin/settings/khong_ton_tai", json={"value": "x"}, headers=auth_header(admin_token)
    )
    assert response.status_code == 404


def test_stats_reflect_data(client: TestClient, admin_token: str, make_user) -> None:
    make_user(email="thong.ke@mindora.test")
    response = client.get("/api/admin/stats", headers=auth_header(admin_token))
    assert response.status_code == 200
    stats = response.json()
    assert set(stats) == {"users", "active_users", "conversations", "questions", "feedback_new"}
    assert stats["users"] >= 2


def test_audit_log_records_admin_actions(client: TestClient, admin_token: str, make_user) -> None:
    from app.db import read_connection

    _, user_id = make_user(email="kiem.toan@mindora.test")
    client.patch("/api/admin/users", json={"user_id": user_id, "role": "admin"}, headers=auth_header(admin_token))
    with read_connection() as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM audit_logs WHERE action = 'update_user' AND target_user_id = ?",
            (user_id,),
        ).fetchone()
    assert int(rows[0]) >= 1


def test_admin_views_user_question_history(
    client: TestClient, admin_token: str, make_user, monkeypatch
) -> None:
    """Quản trị viên xem được toàn bộ hội thoại và tin nhắn của một học viên."""
    from .test_chat import FakeProvider, use_provider

    use_provider(monkeypatch, FakeProvider())
    token, user_id = make_user()
    question = client.post(
        "/api/chat",
        json={"message": "Gradient descent là gì?"},
        headers=auth_header(token),
    ).json()

    response = client.get(
        f"/api/admin/users/{user_id}/history", headers=auth_header(admin_token)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["id"] == user_id
    assert len(body["conversations"]) >= 1
    conversation = next(
        item for item in body["conversations"] if item["id"] == question["conversation_id"]
    )
    roles = [message["role"] for message in conversation["messages"]]
    assert roles == ["user", "assistant"]
    assert conversation["messages"][0]["content"] == "Gradient descent là gì?"


def test_regular_user_cannot_view_history(client: TestClient, make_user) -> None:
    token, user_id = make_user()
    response = client.get(f"/api/admin/users/{user_id}/history", headers=auth_header(token))
    assert response.status_code == 403


def test_admin_history_of_missing_user_is_404(client: TestClient, admin_token: str) -> None:
    response = client.get("/api/admin/users/999999/history", headers=auth_header(admin_token))
    assert response.status_code == 404
