"""Lưu trữ tệp tải lên.

Ba nguyên tắc an toàn:
1. Ghi trực tiếp ra đĩa theo từng khối, không giữ toàn bộ tệp trong bộ nhớ.
2. Kiểm tra dung lượng ngay khi đang ghi nên tệp quá lớn bị dừng ngay.
3. Mọi đường dẫn đều được kiểm tra nằm trong thư mục lưu trữ, chặn path traversal.
"""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ..config import get_settings

READ_BLOCK = 1024 * 1024

FILE_TYPE_BY_EXTENSION = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}

# Dấu hiệu đầu tệp để chống tệp giả mạo đuôi (không cần thư viện nhận diện).
MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF-",),
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
    "image": (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff"),
}


class UploadTooLarge(Exception):
    """Tệp vượt quá dung lượng cho phép."""


class UnsupportedFile(Exception):
    """Định dạng tệp không được hỗ trợ."""


class StorageError(Exception):
    """Lỗi lưu trữ tệp."""


@dataclass(frozen=True)
class StoredFile:
    path: Path
    relative_path: str
    size_kb: int
    content_hash: str
    file_type: str
    extension: str


def resolve_extension(filename: str) -> str:
    """Kiểm tra đuôi tệp theo danh sách cho phép, trả về đuôi chữ thường kèm dấu chấm."""
    settings = get_settings()
    extension = Path(filename or "").suffix.lower()
    if extension not in settings.allowed_upload_types:
        allowed = ", ".join(settings.allowed_upload_types)
        raise UnsupportedFile(f"Chỉ chấp nhận các định dạng: {allowed}.")
    return extension


def file_type_for(extension: str) -> str:
    file_type = FILE_TYPE_BY_EXTENSION.get(extension.lower())
    if not file_type:
        raise UnsupportedFile(f"Không hỗ trợ định dạng {extension}.")
    return file_type


def verify_magic(head: bytes, file_type: str) -> None:
    """Đối chiếu dấu hiệu đầu tệp với định dạng khai báo."""
    signatures = MAGIC_SIGNATURES.get(file_type, ())
    if signatures and not any(head.startswith(signature) for signature in signatures):
        raise UnsupportedFile("Nội dung tệp không khớp với định dạng đã khai báo.")


def ensure_storage_dirs() -> None:
    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_tmp_dir.mkdir(parents=True, exist_ok=True)


def document_dir(user_id: int, document_id: int) -> Path:
    settings = get_settings()
    target = settings.storage_dir / str(user_id) / str(document_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def resolve_stored_path(relative_path: str) -> Path:
    """Trả về đường dẫn tuyệt đối, đảm bảo nằm trong thư mục lưu trữ."""
    settings = get_settings()
    root = settings.storage_dir.resolve()
    candidate = (root / relative_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise StorageError("Đường dẫn tệp không hợp lệ.")
    return candidate


def relative_of(path: Path) -> str:
    settings = get_settings()
    return str(path.resolve().relative_to(settings.storage_dir.resolve()))


async def store_stream(chunks: AsyncIterator[bytes], filename: str, max_mb: int) -> StoredFile:
    """Ghi luồng tệp tải lên vào thư mục tạm, đồng thời kiểm tra dung lượng và dấu hiệu tệp."""
    settings = get_settings()
    ensure_storage_dirs()
    extension = resolve_extension(filename)
    file_type = file_type_for(extension)
    max_bytes = max(1, max_mb) * 1024 * 1024
    temp_path = settings.upload_tmp_dir / f"{uuid4().hex}{extension}"

    digest = hashlib.sha256()
    size = 0
    head = b""
    try:
        with temp_path.open("wb") as handle:
            async for chunk in chunks:
                if not chunk:
                    continue
                if not head:
                    head = chunk[:16]
                size += len(chunk)
                if size > max_bytes:
                    raise UploadTooLarge(f"Tệp vượt quá dung lượng {max_mb} MB cho phép.")
                digest.update(chunk)
                handle.write(chunk)
        if size == 0:
            raise UnsupportedFile("Tệp rỗng.")
        verify_magic(head, file_type)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return StoredFile(
        path=temp_path,
        relative_path=relative_of(temp_path),
        size_kb=max(1, size // 1024),
        content_hash=digest.hexdigest(),
        file_type=file_type,
        extension=extension,
    )


def move_to_document_folder(stored: StoredFile, user_id: int, document_id: int) -> StoredFile:
    """Chuyển tệp tạm sang thư mục của tài liệu sau khi đã có mã tài liệu."""
    target = document_dir(user_id, document_id) / f"original{stored.extension}"
    shutil.move(str(stored.path), str(target))
    return StoredFile(
        path=target,
        relative_path=relative_of(target),
        size_kb=stored.size_kb,
        content_hash=stored.content_hash,
        file_type=stored.file_type,
        extension=stored.extension,
    )


def delete_stored_file(relative_path: str) -> None:
    """Xoá tệp và thư mục rỗng của một tài liệu. Không ném lỗi nếu không tồn tại."""
    try:
        path = resolve_stored_path(relative_path)
    except StorageError:
        return
    path.unlink(missing_ok=True)
    parent = path.parent
    root = get_settings().storage_dir.resolve()
    while parent != root and root in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
