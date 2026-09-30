"""Kiểm thử hạ tầng: cơ sở dữ liệu, migration, định dạng lỗi và health check."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db

from .conftest import auth_header
from .test_chat import FakeProvider, use_provider


def test_migrations_are_idempotent() -> None:
    assert db.run_migrations() == []
    with db.read_connection() as connection:
        assert "001_baseline" in db.applied_migrations(connection)


def test_connection_uses_safe_pragmas() -> None:
    with db.read_connection() as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert int(connection.execute("PRAGMA foreign_keys").fetchone()[0]) == 1
        assert int(connection.execute("PRAGMA busy_timeout").fetchone()[0]) > 0


def test_expected_tables_and_indexes_exist() -> None:
    with db.read_connection() as connection:
        tables = db.table_names(connection)
        indexes = db.index_names(connection)
    assert {"users", "sessions", "system_settings", "audit_logs", "conversations", "messages"} <= tables
    assert {
        "idx_sessions_expires_at",
        "idx_sessions_user_id",
        "idx_conversations_user_id",
        "idx_messages_conversation_id",
        "idx_audit_logs_created_at",
    } <= indexes


def test_error_response_has_code_and_request_id(client: TestClient) -> None:
    response = client.get("/api/khong-ton-tai")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]


def test_health_reports_ok_when_ai_reachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_provider(monkeypatch, FakeProvider())
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["ollama"] == "connected"
    assert body["database"] == "ok"
    assert body["model_available"] is True
    assert body["ollama_models"] == ["qwen2.5:3b"]


def test_health_reports_degraded_when_configured_model_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = FakeProvider()
    provider.list_models = _list_models_empty  # type: ignore[method-assign]
    use_provider(monkeypatch, provider)
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert "no_model_installed" in body["issues"]
    assert body["model_available"] is False


async def _list_models_empty() -> list[str]:
    return []


def test_health_reports_degraded_when_ai_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.llm import LLMUnavailable

    use_provider(monkeypatch, FakeProvider(error=LLMUnavailable("khong ket noi")))
    body = client.get("/api/health").json()
    assert body["status"] == "degraded"
    assert body["database"] == "ok"


def test_ai_model_setting_is_used_and_cache_invalidated(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from app.repositories import settings_repo
    from app.services import llm

    provider = FakeProvider()
    use_provider(monkeypatch, provider, patch_model=False)
    try:
        settings_repo.set_value("ai_model", "qwen2.5:7b")
        assert asyncio.run(llm.resolve_model()) == "qwen2.5:7b"

        client.post(
            "/api/auth/register",
            json={"full_name": "Nguoi dung", "email": "doi.model@mindora.test", "password": "HocTap@123"},
        )
        login = client.post(
            "/api/auth/login", json={"email": "doi.model@mindora.test", "password": "HocTap@123"}
        )
        token = login.json()["token"]
        client.post("/api/chat", json={"message": "Kiem tra model"}, headers={"Authorization": f"Bearer {token}"})
        assert provider.calls and provider.calls[-1][1] == "qwen2.5:7b"
    finally:
        # Tra lai gia tri mac dinh de khong anh huong cac kiem thu khac.
        settings_repo.set_value("ai_model", "qwen2.5:3b")
        llm.invalidate_caches()


def test_changing_model_setting_invalidates_cache(
    client: TestClient, admin_token: str
) -> None:
    import asyncio

    from app.services import llm

    asyncio.run(llm.resolve_model())
    patched = client.patch(
        "/api/admin/settings/ai_model", json={"value": "qwen2.5:7b"}, headers=auth_header(admin_token)
    )
    assert patched.status_code == 200
    try:
        assert asyncio.run(llm.resolve_model()) == "qwen2.5:7b"
    finally:
        client.patch(
            "/api/admin/settings/ai_model", json={"value": "qwen2.5:3b"}, headers=auth_header(admin_token)
        )
        llm.invalidate_caches()


def test_cors_allows_frontend_origin(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
