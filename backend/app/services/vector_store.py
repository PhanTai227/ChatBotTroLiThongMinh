"""Kho vector cục bộ cho RAG, viết bằng thư viện chuẩn của Python.

Vì sao không dùng FAISS/Chroma ngay từ đầu:
- Hệ thống chạy hoàn toàn cục bộ; thêm thư viện vector nặng sẽ làm khó cài đặt và
  Chroma còn tự tải model mặc định từ Internet, vi phạm nguyên tắc offline.
- Ở quy mô đồ án (hàng trăm đến vài nghìn đoạn) phép tính tích vô hướng toàn bộ
  đã đủ nhanh, không cần cấu trúc chỉ mục phức tạp.

Cách lưu trữ:
- Mỗi tài liệu có một tệp nhị phân `vectors.bin` trong thư mục lưu trữ của tài liệu.
- Mỗi bản ghi gồm: số chiều (4 byte), rồi dãy float32.
- Thứ tự bản ghi khớp với `chunks.chunk_index`, nên `chunks.vector_ref` chỉ cần
  lưu dạng "vị trí bản ghi" và việc ánh xạ ngược lại là trực tiếp.

Giao diện `write_vectors` / `search` / `delete_document` cố tình giữ đơn giản để sau
này thay bằng FAISS hoặc Chroma mà không phải sửa mã nghiệp vụ (NFR-2).
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass
from pathlib import Path

from ..config import get_settings
from . import embeddings
from .embeddings import EmbeddingDimensionMismatch

logger = logging.getLogger("mindora.vector_store")

VECTOR_FILE_NAME = "vectors.bin"
_HEADER = struct.Struct("<I")


@dataclass(frozen=True)
class VectorHit:
    """Một kết quả truy hồi: vị trí bản ghi trong tệp vector và điểm tương đồng."""

    document_id: int
    slot: int
    score: float


def vector_dir(user_id: int, document_id: int) -> Path:
    """Thư mục chứa tệp vector, nằm cùng nơi với tệp gốc của tài liệu."""
    settings = get_settings()
    target = settings.storage_dir / str(user_id) / str(document_id)
    target.mkdir(parents=True, exist_ok=True)
    return target


def vector_path(user_id: int, document_id: int) -> Path:
    return vector_dir(user_id, document_id) / VECTOR_FILE_NAME


def _read_records(path: Path, dim: int) -> list[list[float]]:
    """Đọc toàn bộ vector trong tệp. Tệp hỏng thì coi như không có vector."""
    if not path.exists():
        return []
    payload = path.read_bytes()
    vectors: list[list[float]] = []
    offset = 0
    stride = 4 + dim * 4
    while offset + stride <= len(payload):
        (stored_dim,) = _HEADER.unpack_from(payload, offset)
        if stored_dim != dim:
            raise EmbeddingDimensionMismatch(
                f"Tệp vector {path.name} lưu {stored_dim} chiều nhưng cấu hình đang đặt {dim}. "
                "Hãy xoá tệp vector và sinh lại tài liệu."
            )
        start = offset + _HEADER.size
        vectors.append(list(struct.unpack_from(f"<{dim}f", payload, start)))
        offset += stride
    return vectors


def write_vectors(user_id: int, document_id: int, vectors: list[list[float]]) -> int:
    """Ghi đè vector của một tài liệu. Trả về số vector đã lưu.

    Ghi đè toàn bộ thay vì nối thêm để xử lý lại tài liệu không làm dư vector cũ.
    """
    settings = get_settings()
    dim = settings.embedding_dim
    if not vectors:
        return 0
    path = vector_path(user_id, document_id)
    with path.open("wb") as handle:
        for vector in vectors:
            if len(vector) != dim:
                raise EmbeddingDimensionMismatch(
                    f"Vector có {len(vector)} chiều nhưng EMBEDDING_DIM đang đặt {dim}."
                )
            handle.write(_HEADER.pack(dim))
            handle.write(struct.pack(f"<{dim}f", *vector))
    logger.debug("Đã lưu %d vector cho tài liệu %s.", len(vectors), document_id)
    return len(vectors)


def _known_documents(user_id: int, document_ids: list[int] | None) -> list[int]:
    """Danh sách tài liệu cần tìm: đã lọc theo yêu cầu, hoặc toàn bộ của người dùng."""
    settings = get_settings()
    root = settings.storage_dir / str(user_id)
    if not root.exists():
        return []
    if document_ids is not None:
        return [document_id for document_id in document_ids if (root / str(document_id)).exists()]
    found: list[int] = []
    for child in root.iterdir():
        if not child.is_dir() or not child.name.isdigit():
            continue
        if (child / VECTOR_FILE_NAME).exists():
            found.append(int(child.name))
    return found


def search(
    user_id: int,
    query_vector: list[float],
    document_ids: list[int] | None = None,
    top_k: int | None = None,
) -> list[VectorHit]:
    """Tìm các đoạn gần nhất với câu hỏi trong phạm vi tài liệu của người dùng.

    Chỉ tìm trong thư mục lưu trữ của chính người dùng nên không thể truy hồi nhầm
    tài liệu của người khác (NFR-3).
    """
    settings = get_settings()
    limit = top_k or settings.rag_top_k
    if limit < 1:
        return []

    hits: list[VectorHit] = []
    for document_id in _known_documents(user_id, document_ids):
        vectors = _read_records(vector_path(user_id, document_id), settings.embedding_dim)
        for slot, vector in enumerate(vectors):
            hits.append(
                VectorHit(
                    document_id=document_id,
                    slot=slot,
                    score=embeddings.cosine_similarity(query_vector, vector),
                )
            )

    # Sắp xếp giảm dần theo điểm; khi hòng điểm thì ưu tiên tài liệu nhỏ hơn để ổn định.
    hits.sort(key=lambda hit: (-hit.score, hit.document_id, hit.slot))
    return hits[:limit]


def delete_document(user_id: int, document_id: int) -> None:
    """Xoá tệp vector của tài liệu. Không ném lỗi nếu không tồn tại."""
    try:
        vector_path(user_id, document_id).unlink(missing_ok=True)
    except OSError as exc:  # pragma: no cover - phụ thuộc hệ thống tệp
        logger.warning("Không xoá được tệp vector của tài liệu %s: %s", document_id, exc)
