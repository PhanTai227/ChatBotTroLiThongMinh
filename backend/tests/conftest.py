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
os.environ["STORAGE_DIR"] = str(_TMP_DIR / "storage")
os.environ["UPLOAD_TMP_DIR"] = str(_TMP_DIR / "storage" / "tmp")
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


@pytest.fixture
def docx_factory():
    """Tạo tệp DOCX hợp lệ với tiêu đề tuỳ ý, dùng để sinh dữ liệu kiểm thử."""
    import io

    import docx

    def _make(title: str, paragraphs: int = 5) -> bytes:
        document = docx.Document()
        document.add_heading(title, level=1)
        for index in range(1, paragraphs + 1):
            document.add_paragraph(
                f"Muc {index}. Gradient descent la thuat toan toi uu ham mat sat theo huong giam dan. "
                f"Noi dung muc {index} cua {title}."
            )
        buffer = io.BytesIO()
        document.save(buffer)
        return buffer.getvalue()

    return _make


@pytest.fixture
def sample_docx(docx_factory) -> bytes:
    return docx_factory("Giáo trình Trí tuệ nhân tạo")


@pytest.fixture
def sample_pdf() -> bytes:
    """Tạo một tệp PDF hợp lệ có lớp chữ để kiểm thử trích xuất."""
    import fitz

    document = fitz.open()
    for page_index in range(2):
        page = document.new_page()
        page.insert_text((72, 100), f"Trang {page_index + 1}: noi dung bai giang ve hoc tap.")
        page.insert_text((72, 130), "Gradient descent toi uu hoa ham mat sat bang buoc lap.")
    payload = document.tobytes()
    document.close()
    return payload


@pytest.fixture
def upload(client: TestClient):
    """Hàm tiện ích tải tệp lên và trả về (status_code, body)."""

    def _upload(
        token: str,
        content: bytes,
        filename: str = "tai-lieu.pdf",
        content_type: str = "application/pdf",
        **fields: str,
    ):
        return client.post(
            "/api/documents",
            files={"file": (filename, content, content_type)},
            data=fields or None,
            headers=auth_header(token),
        )

    return _upload
