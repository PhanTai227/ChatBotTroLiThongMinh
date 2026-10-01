"""Sinh vector nhúng từ văn bản, phục vụ tìm kiếm ngữ nghĩa (RAG).

Dùng cùng một dịch vụ Ollama đang phục vụ LLM nên hệ thống vẫn chạy hoàn toàn
cục bộ, không thêm thư viện vector nào (chỉ dùng thư viện chuẩn của Python).

Mọi vector đều được chuẩn hoá về độ dài 1, nhờ đó tích vô hướng chính là
điểm tương đồng cosine: điểm càng gần 1 thì hai câu càng giống nhau.
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from ..config import get_settings
from ..repositories import settings_repo

logger = logging.getLogger("mindora.embeddings")

_MODEL_CACHE_TTL_SECONDS = 60.0
_CONNECT_ATTEMPTS = 2


class EmbeddingError(Exception):
    """Lỗi chung của dịch vụ vector nhúng."""


class EmbeddingUnavailable(EmbeddingError):
    """Không kết nối được tới Ollama để sinh vector."""


class EmbeddingTimeout(EmbeddingError):
    """Sinh vector quá lâu."""


class EmbeddingModelMissing(EmbeddingError):
    """Ollama không có model embedding được cấu hình."""


class EmbeddingDimensionMismatch(EmbeddingError):
    """Vector trả về không đúng số chiều đã khai báo trong cấu hình."""


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model: str


def normalize(vector: list[float]) -> list[float]:
    """Đưa vector về độ dài 1 để tích vô hướng = cosine similarity."""
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Điểm tương đồng cosine của hai vector đã chuẩn hoá."""
    if len(left) != len(right):
        raise EmbeddingDimensionMismatch(f"Hai vector khác số chiều: {len(left)} và {len(right)}.")
    return sum(a * b for a, b in zip(left, right, strict=True))
class OllamaEmbeddingProvider:
    """Sinh vector nhúng qua endpoint /api/embed của Ollama."""

    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.ollama_host
        self._dim = settings.embedding_dim
        self._timeout = httpx.Timeout(settings.llm_timeout_seconds, connect=10.0)

    async def embed(self, texts: list[str], model: str) -> EmbeddingResult:
        if not texts:
            return EmbeddingResult(vectors=[], model=model)
        payload = {"model": model, "input": list(texts), "keep_alive": "10m"}
        response = await self._post(f"{self._host}/api/embed", payload, self._timeout)
        if response.status_code == 404:
            raise EmbeddingModelMissing(f"Ollama không có model embedding {model!r}.")
        if response.status_code >= 400:
            raise EmbeddingUnavailable(f"Ollama trả về mã lỗi {response.status_code}.")
        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingUnavailable("Ollama trả về dữ liệu không hợp lệ.") from exc

        raw = data.get("embeddings")
        if raw is None and isinstance(data.get("embedding"), list):
            raw = [data["embedding"]]
        if not isinstance(raw, list) or len(raw) != len(texts):
            raise EmbeddingUnavailable("Ollama trả về số vector không khớp số đoạn văn bản.")

        vectors: list[list[float]] = []
        for item in raw:
            if not isinstance(item, list) or not item:
                raise EmbeddingUnavailable("Ollama trả về vector rỗng hoặc sai định dạng.")
            if len(item) != self._dim:
                raise EmbeddingDimensionMismatch(
                    f"Model trả về {len(item)} chiều nhưng EMBEDDING_DIM đang đặt {self._dim}. "
                    "Hãy sửa EMBEDDING_DIM cho khớp model và sinh lại vector cũ."
                )
            vectors.append(normalize([float(value) for value in item]))
        return EmbeddingResult(vectors=vectors, model=model)

    async def _post(self, url: str, payload: dict, timeout: httpx.Timeout) -> httpx.Response:
        last_error: httpx.HTTPError | None = None
        for attempt in range(1, _CONNECT_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    return await client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                raise EmbeddingTimeout("Sinh vector quá lâu.") from exc
            except httpx.ConnectError as exc:
                # Ollama có thể đang khởi động: thử lại một lần trước khi báo lỗi.
                last_error = exc
                if attempt < _CONNECT_ATTEMPTS:
                    await asyncio.sleep(1.0)
            except httpx.HTTPError as exc:
                raise EmbeddingUnavailable("Không kết nối được máy chủ AI.") from exc
        raise EmbeddingUnavailable("Không kết nối được máy chủ AI.") from last_error
_provider: OllamaEmbeddingProvider | None = None
_model_cache: tuple[float, str] | None = None


def get_provider() -> OllamaEmbeddingProvider:
    """Trả về provider sinh vector (khởi tạo một lần cho cả tiến trình)."""
    global _provider
    if _provider is None:
        _provider = OllamaEmbeddingProvider()
    return _provider


async def resolve_model() -> str:
    """Model embedding: ưu tiên giá trị admin đặt trong system_settings, đệm 60 giây."""
    global _model_cache
    settings = get_settings()
    now = time.monotonic()
    if _model_cache and now - _model_cache[0] < _MODEL_CACHE_TTL_SECONDS:
        return _model_cache[1]
    model = settings_repo.get_value("embedding_model", settings.embedding_model) or settings.embedding_model
    _model_cache = (now, model)
    return model


def iter_batches(texts: list[str], size: int) -> Iterator[list[str]]:
    """Chia danh sách văn bản thành các lô không vượt quá `size` phần tử."""
    if size < 1:
        raise ValueError("Kích thước lô phải từ 1 trở lên.")
    for start in range(0, len(texts), size):
        yield texts[start : start + size]


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Sinh vector cho nhiều đoạn văn bản, tự chia lô theo EMBEDDING_BATCH_SIZE."""
    if not texts:
        return []
    settings = get_settings()
    model = await resolve_model()
    provider = get_provider()

    vectors: list[list[float]] = []
    for batch in iter_batches(texts, settings.embedding_batch_size):
        vectors.extend((await provider.embed(batch, model)).vectors)
    logger.debug("Đã sinh %d vector bằng model %s.", len(vectors), model)
    return vectors


async def embed_query(text: str) -> list[float]:
    """Sinh vector cho một câu hỏi."""
    vectors = await embed_texts([text])
    if not vectors:
        raise EmbeddingUnavailable("Không sinh được vector cho câu hỏi.")
    return vectors[0]


def invalidate_caches() -> None:
    """Xoá cache của dịch vụ vector nhúng, dùng khi cấu hình thay đổi hoặc trong kiểm thử."""
    global _provider, _model_cache
    _provider = None
    _model_cache = None
