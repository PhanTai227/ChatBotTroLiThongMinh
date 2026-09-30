"""Kiểm thử nhóm xác thực."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import ADMIN_EMAIL, ADMIN_PASSWORD, auth_header


def test_register_returns_token_and_user(client: TestClient, make_user) -> None:
    token, user_id = make_user(email="moi.dang.ky@mindora.test")
    assert token and user_id > 0

    response = client.get("/api/auth/me", headers=auth_header(token))
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "moi.dang.ky@mindora.test"


def test_register_duplicate_email_conflict(client: TestClient, make_user) -> None:
    make_user(email="trung.email@mindora.test")
    response = client.post(
        "/api/auth/register",
        json={"full_name": "Người dùng khác", "email": "trung.email@mindora.test", "password": "HocTap@123"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


def test_register_validation_error(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register", json={"full_name": "A", "email": "a@b", "password": "123"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert any(field["field"] == "password" for field in body["fields"])


def test_login_success_updates_last_login(client: TestClient, make_user) -> None:
    make_user(email="dang.nhap@mindora.test", password="HocTap@123")
    response = client.post(
        "/api/auth/login", json={"email": "dang.nhap@mindora.test", "password": "HocTap@123"}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "user"

    admin = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    users = client.get("/api/admin/users", headers=auth_header(admin.json()["token"])).json()
    target = next(user for user in users if user["email"] == "dang.nhap@mindora.test")
    assert target["last_login_at"] is not None


def test_login_wrong_password(client: TestClient, make_user) -> None:
    make_user(email="sai.mat.khau@mindora.test", password="HocTap@123")
    response = client.post(
        "/api/auth/login", json={"email": "sai.mat.khau@mindora.test", "password": "SaiMatKhau@1"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_login_locked_account(client: TestClient, make_user, admin_token: str) -> None:
    _, user_id = make_user(email="bi.khoa@mindora.test", password="HocTap@123")
    patched = client.patch(
        "/api/admin/users", json={"user_id": user_id, "is_active": False}, headers=auth_header(admin_token)
    )
    assert patched.status_code == 200

    response = client.post(
        "/api/auth/login", json={"email": "bi.khoa@mindora.test", "password": "HocTap@123"}
    )
    assert response.status_code == 403


def test_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_logout_invalidates_session(client: TestClient, make_user) -> None:
    token, _ = make_user()
    assert client.post("/api/auth/logout", headers=auth_header(token)).status_code == 200
    assert client.get("/api/auth/me", headers=auth_header(token)).status_code == 401
