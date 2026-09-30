"""Thiết lập cho kiểm thử: dùng cơ sở dữ liệu tạm, không chạm vào dữ liệu thật.

Biến môi trường phải được đặt trước khi import app, vì cấu hình được đọc
lười ở lần gọi đầu tiên.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_TMP_DIR = Path(tempfile.mkdtemp(prefix="mindora-test-"))
os.environ["DATABASE_PATH"] = str(_TMP_DIR / "test.db")
os.environ["LOG_TO_FILE"] = "false"
os.environ["LLM_TIMEOUT_SECONDS"] = "5"
os.environ["HEALTH_TIMEOUT_SECONDS"] = "1"
os.environ["PBKDF2_ITERATIONS"] = "1000"

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app as fastapi_app
from app.services import llm

ADMIN_EMAIL = "admin@mindora.local"
ADMIN_PASSWORD = "Admin@123"


@pytest.fixture(scope="session", autouse=True)
def _cleanup_temp_database() -> Iterator[None]:
    yield
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(fastapi_app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _reset_caches() -> Iterator[None]:
    config.reset_settings_cache()
    llm.invalidate_caches()
    yield
    llm.invalidate_caches()


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    response = client.post(
        "/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.fixture
def make_user(client: TestClient):
    """Tạo tài khoản mới và trả về (token, user_id). Email luôn duy nhất."""
    from uuid import uuid4

    def _make(email: str | None = None, password: str = "HocTap@123") -> tuple[str, int]:
        address = email or f"hocvien-{uuid4().hex[:8]}@mindora.test"
        response = client.post(
            "/api/auth/register",
            json={"full_name": "Hoc vien thu", "email": address, "password": password},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        return body["token"], int(body["user"]["id"])

    return _make


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
