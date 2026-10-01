"""Tìm kiếm ngữ nghĩa trong kho tài liệu của người dùng (FR-B3).

Luồng: câu hỏi -> vector nhúng -> tìm top-k đoạn gần nhất -> lọc theo ngưỡng
-> bổ sung thông tin hiển thị (tên tệp, số trang, trích đoạn) để làm nguồn trích dẫn.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..config import get_settings
from ..repositories import chunks as chunks_repo
from ..repositories import documents as documents_repo
from . import embeddings, vector_store

logger = logging.getLogger("mindora.retrieval")

SNIPPET_MAX_CHARS = 320


@dataclass(frozen=True)
class RetrievedChunk:
    """Một đoạn văn bản tìm được, kèm thông tin đủ để trích dẫn."""

    document_id: int
    chunk_id: int
    content: str
    file_name: str
    page_number: int | None
    score: float

    @property
    def snippet(self) -> str:
        return make_snippet(self.content)


def make_snippet(content: str) -> str:
    """Rút gọn nội dung để hiển thị trong danh sách nguồn."""
    text = " ".join((content or "").split())
    if len(text) <= SNIPPET_MAX_CHARS:
        return text
    return text[: SNIPPET_MAX_CHARS - 1].rstrip() + "…"


async def search(
    owner_id: int,
    question: str,
    document_id: int | None = None,
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """Trả về các đoạn liên quan tới câu hỏi.

    Chỉ tìm trong tài liệu của chính `owner_id`; nếu có `document_id` thì giới hạn
    trong đúng tài liệu đó. Kết quả dưới `RAG_MIN_SCORE` bị loại để tránh dùng
    ngữ cảnh không liên quan (NFR-4).
    """
    settings = get_settings()
    limit = top_k or settings.rag_top_k
    if limit < 1:
        return []

    if document_id is not None and not documents_repo.get_owned(document_id, owner_id):
        return []

    query_vector = await embeddings.embed_query(question)
    hits = vector_store.search(owner_id, query_vector, [document_id] if document_id else None, limit)

    results: list[RetrievedChunk] = []
    seen: set[int] = set()
    documents_cache: dict[int, dict | None] = {}
    for hit in hits:
        if hit.score < settings.rag_min_score:
            break
        row = chunks_repo.get_by_index(hit.document_id, hit.slot)
        if not row or int(row["id"]) in seen:
            continue
        seen.add(int(row["id"]))
        if hit.document_id not in documents_cache:
            row_document = documents_repo.get_by_id(hit.document_id)
            documents_cache[hit.document_id] = dict(row_document) if row_document else None
        document = documents_cache[hit.document_id]
        if not document:
            continue
        results.append(
            RetrievedChunk(
                document_id=hit.document_id,
                chunk_id=int(row["id"]),
                content=str(row["content"]),
                file_name=str(document["file_name"]),
                page_number=row["page_number"],
                score=round(hit.score, 4),
            )
        )
    logger.debug("Tìm được %d đoạn cho câu hỏi của người dùng %s.", len(results), owner_id)
    return results


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Ghép các đoạn tìm được thành khối ngữ cảnh có đánh số nguồn cho LLM."""
    settings = get_settings()
    blocks: list[str] = []
    used = 0
    for position, chunk in enumerate(chunks, start=1):
        location = chunk.file_name
        if chunk.page_number:
            location = f"{location} (trang {chunk.page_number})"
        block = f"[{position}] Nguồn: {location}\n{chunk.content}"
        if used + len(block) > settings.rag_context_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)
