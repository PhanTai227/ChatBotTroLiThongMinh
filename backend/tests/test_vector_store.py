"""Kiểm thử kho vector cục bộ: ghi, đọc, xếp hạng và cách xoá."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import embeddings, vector_store


def _vector(value: float, dim: int | None = None) -> list[float]:
    """Vector đơn vị dọc theo một chiều, thuận tiện cho kiểm thử."""
    size = dim or get_settings().embedding_dim
    vector = [0.0] * size
    vector[0] = value
    return embeddings.normalize(vector)


def test_write_and_search_ranks_similar_first(tmp_path) -> None:
    settings = get_settings()
    # Kho vector dùng chung STORAGE_DIR của bộ kiểm thử nên dùng user giả lập riêng.
    user_id = 900_001
    document_id = 900_001
    vectors = [_vector(1.0), _vector(0.6), _vector(0.1)]
    assert vector_store.write_vectors(user_id, document_id, vectors) == 3

    hits = vector_store.search(user_id, _vector(1.0), [document_id], top_k=3)
    assert [hit.slot for hit in hits] == [0, 1, 2]
    assert hits[0].score >= hits[1].score >= hits[2].score
    assert hits[0].document_id == document_id

    vector_store.delete_document(user_id, document_id)
    assert not settings.storage_dir.joinpath(str(user_id), str(document_id), vector_store.VECTOR_FILE_NAME).exists()


def test_search_respects_top_k() -> None:
    user_id, document_id = 900_002, 900_002
    vector_store.write_vectors(user_id, document_id, [_vector(1.0), _vector(0.9), _vector(0.8)])
    try:
        assert len(vector_store.search(user_id, _vector(1.0), [document_id], top_k=2)) == 2
    finally:
        vector_store.delete_document(user_id, document_id)


def test_search_is_scoped_to_owner() -> None:
    """Người dùng khác không tìm thấy vector của người này (NFR-3)."""
    owner_id, other_id = 900_003, 900_004
    document_id = 900_003
    vector_store.write_vectors(owner_id, document_id, [_vector(1.0)])
    try:
        assert vector_store.search(other_id, _vector(1.0), [document_id], top_k=5) == []
        assert len(vector_store.search(owner_id, _vector(1.0), top_k=5)) == 1
    finally:
        vector_store.delete_document(owner_id, document_id)


def test_search_returns_empty_for_unknown_user() -> None:
    assert vector_store.search(900_005, _vector(1.0), top_k=5) == []


def test_write_rejects_wrong_dimension() -> None:
    with pytest.raises(embeddings.EmbeddingDimensionMismatch):
        vector_store.write_vectors(900_006, 900_006, [[1.0, 0.0, 0.0]])


def test_delete_document_is_safe_when_missing() -> None:
    vector_store.delete_document(900_007, 900_007)  # không ném lỗi


def test_search_with_zero_top_k_returns_empty() -> None:
    assert vector_store.search(900_008, _vector(1.0), top_k=0) == []
