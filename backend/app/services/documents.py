"""Quy trình xử lý tài liệu: trích xuất văn bản, chia đoạn, lưu vào cơ sở dữ liệu.

Luồng: documents(status=uploading) -> ocr_processing -> ready | error
Việc nặng chạy nền qua hàng đợi `processing_jobs` nên tải lên không bị chặn.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..config import get_settings
from ..repositories import chunks as chunks_repo
from ..repositories import documents as documents_repo
from ..repositories import jobs as jobs_repo
from . import chunking, embeddings, extraction, storage, vector_store

logger = logging.getLogger("mindora.documents")

# Luồng xử lý: uploading -> ocr_processing -> embedding -> ready | error
STAGE_EMBEDDING = jobs_repo.STAGE_EMBEDDING


@dataclass
class PipelineOutcome:
    document_id: int
    chunk_count: int
    page_count: int
    method: str
    warnings: list[str] = field(default_factory=list)


class DocumentNotFound(Exception):
    """Không tìm thấy tài liệu trong cơ sở dữ liệu hoặc trên đĩa."""


def document_path(storage_path: str) -> Path:
    return storage.resolve_stored_path(storage_path)


def process_document(document_id: int) -> PipelineOutcome:
    """Trích xuất và chia đoạn một tài liệu. Ném lỗi nếu không đọc được nội dung."""
    document = documents_repo.get_by_id(document_id)
    if not document:
        raise DocumentNotFound(f"Không tìm thấy tài liệu {document_id}.")

    settings = get_settings()
    path = document_path(document["storage_path"])
    try:
        result = extraction.extract(path, document["file_type"])
        chunks = chunking.split_pages(result.pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise extraction.ExtractionError(
                "Không tìm thấy nội dung chữ trong tài liệu. "
                "Nếu là PDF scan, hãy kiểm tra lại cấu hình OCR."
            )
        chunks_repo.replace_chunks(
            document_id,
            [(chunk.index, chunk.content, chunk.page_number, chunk.token_estimate) for chunk in chunks],
        )
    except Exception as exc:
        documents_repo.set_status(document_id, "error", error_message=str(exc))
        raise

    documents_repo.set_status(
        document_id,
        "embedding",
        page_count=result.page_count,
        extract_method=result.method,
    )
    # Đẩy sang giai đoạn sinh vector để tài liệu chỉ "ready" khi đã có thể truy hồi.
    jobs_repo.enqueue(document_id, STAGE_EMBEDDING)
    for warning in result.warnings:
        logger.warning("Tài liệu %d: %s", document_id, warning)
    return PipelineOutcome(
        document_id=document_id,
        chunk_count=len(chunks),
        page_count=result.page_count,
        method=result.method,
        warnings=result.warnings,
    )


async def embed_document(document_id: int) -> int:
    """Sinh vector cho từng đoạn của tài liệu và lưu vào kho vector cục bộ.

    Chỉ cần đọc nội dung chunk đã có nên các tài liệu cũ cũng sinh lại được vector
    mà không phải trích xuất lại từ tệp gốc.
    """
    document = documents_repo.get_by_id(document_id)
    if not document:
        raise DocumentNotFound(f"Không tìm thấy tài liệu {document_id}.")

    rows = chunks_repo.list_pending_vector_refs(document_id)
    if not rows:
        # Đã có vector đủ cho mọi chunk: chỉ cần chốt trạng thái là xong.
        documents_repo.set_status(document_id, "ready")
        return 0

    owner_id = int(document["owner_id"])
    texts = [str(row["content"]) for row in rows]
    vectors = await embeddings.embed_texts(texts)
    if len(vectors) != len(rows):
        raise embeddings.EmbeddingError("Số vector nhận được không khớp số đoạn cần embedding.")

    vector_store.write_vectors(owner_id, document_id, vectors)
    refs = {
        int(row["chunk_index"]): f"{document_id}#{position}"
        for position, row in enumerate(rows)
    }
    chunks_repo.set_vector_refs(document_id, refs)
    documents_repo.set_status(document_id, "ready")
    logger.info("Tài liệu %s đã có %d vector nhúng.", document_id, len(vectors))
    return len(vectors)


async def _embed_with_retries(job: sqlite3.Row) -> None:
    attempts = int(job["attempts"])
    max_attempts = get_settings().max_attempts
    document_id = int(job["document_id"])
    try:
        count = await embed_document(document_id)
    except Exception as exc:  # noqa: BLE001 - mọi lỗi đều phải được ghi nhận rồi thử lại
        if attempts >= max_attempts:
            jobs_repo.mark_failed(int(job["id"]), str(exc), retry_at=None)
            documents_repo.set_status(document_id, "error", error_message=str(exc))
            logger.error("Sinh vector cho tài liệu %s thất bại sau %d lần: %s", document_id, attempts, exc)
            return
        delay = jobs_repo.next_backoff_seconds(attempts)
        jobs_repo.mark_failed(int(job["id"]), str(exc), retry_at=datetime.now(UTC) + timedelta(seconds=delay))
        logger.warning("Sinh vector tài liệu %s lỗi (lần %d), thử lại sau %ds: %s", document_id, attempts, delay, exc)
        return
    jobs_repo.mark_done(int(job["id"]))
    logger.info("Hoàn tất sinh vector cho tài liệu %s (%d vector).", document_id, count)


async def _process_with_retries(job: sqlite3.Row) -> None:
    """Chạy đúng hàm xử lý theo giai đoạn của việc."""
    if job["stage"] == STAGE_EMBEDDING:
        await _embed_with_retries(job)
        return

    attempts = int(job["attempts"])
    max_attempts = get_settings().max_attempts
    try:
        outcome = process_document(int(job["document_id"]))
    except Exception as exc:  # noqa: BLE001 - mọi lỗi đều phải được ghi nhận rồi thử lại
        if attempts >= max_attempts:
            jobs_repo.mark_failed(int(job["id"]), str(exc), retry_at=None)
            logger.error("Xử lý tài liệu %s thất bại sau %d lần: %s", job["document_id"], attempts, exc)
            return
        delay = jobs_repo.next_backoff_seconds(attempts)
        jobs_repo.mark_failed(
            int(job["id"]), str(exc), retry_at=datetime.now(UTC) + timedelta(seconds=delay)
        )
        logger.warning(
            "Xử lý tài liệu %s lỗi (lần %d), thử lại sau %ds: %s",
            job["document_id"], attempts, delay, exc,
        )
        return
    jobs_repo.mark_done(int(job["id"]))
    logger.info(
        "Tài liệu %s đã trích xuất: %d đoạn, %d trang, cách đọc %s",
        outcome.document_id, outcome.chunk_count, outcome.page_count, outcome.method,
    )


async def run_pending_jobs(limit: int = 20) -> int:
    """Xử lý các việc đang chờ. Dùng cho cả nền tảng và lúc khởi động.

    Vòng lặp bên ngoài đi qua từng giai đoạn (OCR rồi embedding) vì một việc OCR
    vừa xong sẽ tạo thêm một việc embedding mới.
    """
    processed = 0
    for stage in (jobs_repo.STAGE_OCR, STAGE_EMBEDDING):
        for _ in range(limit):
            job = jobs_repo.claim_next(stage)
            if not job:
                break
            await _process_with_retries(job)
            processed += 1
    return processed


async def recover_on_startup() -> None:
    """Đưa việc bị kẹt về hàng đợi và xử lý tiếp khi khởi động."""
    requeued = jobs_repo.requeue_stale()
    if requeued:
        logger.info("Đã đưa %d việc bị kẹt trở lại hàng đợi.", requeued)
    await run_pending_jobs()


def delete_document_files(document: dict) -> None:
    """Xoá tệp gốc và tệp vector của tài liệu."""
    document_id = int(document["id"]) if document.get("id") else None
    owner_id = int(document["owner_id"]) if document.get("owner_id") else None
    if document_id is not None and owner_id is not None:
        vector_store.delete_document(owner_id, document_id)
    try:
        storage.delete_stored_file(document["storage_path"])
    except storage.StorageError as exc:
        logger.warning("Không xoá được tệp của tài liệu %s: %s", document.get("id"), exc)
