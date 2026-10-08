"""Kiểm thử phản hồi: học viên gửi đánh giá, quản trị viên xem và trả lời."""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import auth_header


def test_feedback_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/feedback", json={"rating": 5, "content": "Tốt"}).status_code == 401
    assert client.get("/api/feedback").status_code == 401


def test_user_sends_feedback_and_sees_own(client: TestClient, make_user) -> None:
    token, _ = make_user()
    created = client.post(
        "/api/feedback",
        json={"rating": 5, "category": "praise", "content": "Trả lời rất nhanh và chính xác."},
        headers=auth_header(token),
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "new"

    listed = client.get("/api/feedback", headers=auth_header(token)).json()
    assert len(listed["items"]) == 1
    assert listed["items"][0]["rating"] == 5


def test_feedback_validates_rating_and_content(client: TestClient, make_user) -> None:
    token, _ = make_user()
    assert (
        client.post(
            "/api/feedback",
            json={"rating": 6, "content": "quá cao"},
            headers=auth_header(token),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/feedback",
            json={"rating": 3, "content": "   "},
            headers=auth_header(token),
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/feedback",
            json={"rating": 3, "content": "sai category", "category": "spam"},
            headers=auth_header(token),
        ).status_code
        == 422
    )


def test_user_cannot_read_admin_feedback(client: TestClient, make_user) -> None:
    token, _ = make_user()
    assert client.get("/api/admin/feedback", headers=auth_header(token)).status_code == 403


def test_admin_lists_replies_and_marks_read(
    client: TestClient, admin_token: str, make_user
) -> None:
    token, user_id = make_user()
    created = client.post(
        "/api/feedback",
        json={"rating": 2, "category": "bug", "content": "Upload PDF bị lỗi."},
        headers=auth_header(token),
    ).json()

    listed = client.get("/api/admin/feedback", headers=auth_header(admin_token)).json()
    match = next(item for item in listed["items"] if item["id"] == created["id"])
    assert match["email"].endswith("@mindora.test")
    assert match["user_id"] == user_id
    assert match["status"] == "new"

    marked = client.patch(
        f"/api/admin/feedback/{created['id']}", headers=auth_header(admin_token)
    )
    assert marked.status_code == 200

    replied = client.post(
        f"/api/admin/feedback/{created['id']}/reply",
        json={"admin_reply": "Cảm ơn bạn, chúng tôi đã sửa."},
        headers=auth_header(admin_token),
    )
    assert replied.status_code == 200

    # Học viên thấy trả lời trong trang phản hồi của mình.
    mine = client.get("/api/feedback", headers=auth_header(token)).json()["items"][0]
    assert mine["status"] == "replied"
    assert mine["admin_reply"] == "Cảm ơn bạn, chúng tôi đã sửa."


def test_admin_feedback_404_when_missing(client: TestClient, admin_token: str) -> None:
    assert client.patch("/api/admin/feedback/999999", headers=auth_header(admin_token)).status_code == 404
    assert (
        client.post(
            "/api/admin/feedback/999999/reply",
            json={"admin_reply": "alo"},
            headers=auth_header(admin_token),
        ).status_code
        == 404
    )
