"""Kiểm thử dịch vụ vector nhúng: chuẩn hoá, cosine và cách chia lô."""

from __future__ import annotations

import math

import pytest

from app.config import get_settings
from app.services import embeddings

from .conftest import REAL_EMBED_TEXTS


def test_normalize_makes_unit_vector() -> None:
    vector = embeddings.normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(value * value for value in vector)), 1.0, rel_tol=1e-9)
    assert vector == [pytest.approx(0.6), pytest.approx(0.8)]


def test_normalize_handles_zero_vector() -> None:
    assert embeddings.normalize([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0]


def test_cosine_similarity_of_identical_vectors_is_one() -> None:
    vector = embeddings.normalize([1.0, 2.0, 3.0])
    assert embeddings.cosine_similarity(vector, vector) == pytest.approx(1.0)


def test_cosine_similarity_of_opposite_vectors_is_minus_one() -> None:
    left = embeddings.normalize([1.0, 0.0])
    right = embeddings.normalize([-1.0, 0.0])
    assert embeddings.cosine_similarity(left, right) == pytest.approx(-1.0)


def test_cosine_similarity_rejects_dimension_mismatch() -> None:
    with pytest.raises(embeddings.EmbeddingDimensionMismatch):
        embeddings.cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0])


def test_iter_batches_splits_evenly_and_leftovers() -> None:
    assert [list(batch) for batch in embeddings.iter_batches(["a", "b", "c"], 2)] == [["a", "b"], ["c"]]
    assert [list(batch) for batch in embeddings.iter_batches(["a", "b"], 5)] == [["a", "b"]]
    assert list(embeddings.iter_batches([], 3)) == []


def test_iter_batches_rejects_invalid_size() -> None:
    with pytest.raises(ValueError):
        list(embeddings.iter_batches(["a"], 0))


def test_embed_texts_calls_provider_once_per_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mỗi lô chỉ gọi provider đúng một lần và gộp đủ số vector."""
    import asyncio

    batch_calls: list[list[str]] = []

    class FakeProvider:
        async def embed(self, texts: list[str], model: str) -> embeddings.EmbeddingResult:
            batch_calls.append(list(texts))
            dim = get_settings().embedding_dim
            return embeddings.EmbeddingResult(
                vectors=[embeddings.normalize([1.0] + [0.0] * (dim - 1)) for _ in texts], model=model
            )

    async def fake_model() -> str:
        return "nomic-embed-text"

    monkeypatch.setattr(embeddings, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(embeddings, "resolve_model", fake_model)
    # 3 đoạn nhỏ hơn EMBEDDING_BATCH_SIZE mặc định nên chỉ gọi provider một lần.
    vectors = asyncio.run(REAL_EMBED_TEXTS(["a", "b", "c"]))

    assert len(vectors) == 3
    assert [len(call) for call in batch_calls] == [3]


def test_embed_texts_splits_when_exceeding_batch_size(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vượt quá EMBEDDING_BATCH_SIZE thì phải chia thành nhiều lô."""
    import asyncio

    from app.config import get_settings

    batch_calls: list[list[str]] = []

    class FakeProvider:
        async def embed(self, texts: list[str], model: str) -> embeddings.EmbeddingResult:
            batch_calls.append(list(texts))
            dim = get_settings().embedding_dim
            return embeddings.EmbeddingResult(
                vectors=[embeddings.normalize([1.0] + [0.0] * (dim - 1)) for _ in texts], model=model
            )

    async def fake_model() -> str:
        return "nomic-embed-text"

    monkeypatch.setattr(embeddings, "get_provider", lambda: FakeProvider())
    monkeypatch.setattr(embeddings, "resolve_model", fake_model)

    texts = ["a", "b", "c", "d", "e"]
    total = 0
    for batch in embeddings.iter_batches(texts, 2):
        total += len(asyncio.run(REAL_EMBED_TEXTS(batch)))

    assert [len(call) for call in batch_calls] == [2, 2, 1]
    assert total == len(texts)


def test_embed_texts_with_empty_input_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Danh sách rỗng thì không gọi provider nào."""
    import asyncio

    calls: list[list[str]] = []

    class FakeProvider:
        async def embed(self, texts: list[str], model: str) -> embeddings.EmbeddingResult:
            calls.append(list(texts))
            return embeddings.EmbeddingResult(vectors=[], model=model)

    monkeypatch.setattr(embeddings, "get_provider", lambda: FakeProvider())
    assert asyncio.run(REAL_EMBED_TEXTS([])) == []
    assert calls == []
