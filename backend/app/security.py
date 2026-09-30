"""Bảo mật: băm mật khẩu và sinh token phiên đăng nhập.

Không phụ thuộc thư viện ngoài: dùng `hashlib.pbkdf2_hmac` của thư viện chuẩn
để hệ thống chạy cục bộ hoàn toàn, không cần cài thêm gói bảo mật.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from .config import get_settings

_ALGORITHM = "pbkdf2_sha256"
_SALT_BYTES = 16
_TOKEN_BYTES = 48


def hash_password(password: str, iterations: int | None = None) -> str:
    """Băm mật khẩu theo định dạng pbkdf2_sha256$<số vòng>$<salt>$<digest>."""
    rounds = iterations or get_settings().pbkdf2_iterations
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return f"{_ALGORITHM}${rounds}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Kiểm tra mật khẩu, luôn trả về False thay vì ném lỗi khi dữ liệu hỏng."""
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        if algorithm != _ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
    except (AttributeError, TypeError, ValueError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def password_needs_rehash(encoded: str) -> bool:
    """True nếu mật khẩu đã băm bằng số vòng lặp thấp hơn cấu hình hiện tại."""
    try:
        _, iterations, _, _ = encoded.split("$")
        return int(iterations) < get_settings().pbkdf2_iterations
    except (AttributeError, TypeError, ValueError):
        return True


def new_session_token() -> str:
    """Sinh token phiên ngẫu nhiên 48 byte (384 bit entropy)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Băm token, dùng khi chuyển sang lưu phiên không dạng văn bản thô."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
