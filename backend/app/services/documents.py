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
from . import chunking, extraction, storage

logger = logging.getLogger("mindora.documents")

STAGE_EMBEDDING = "embedding"  # Giai đoạn sinh vector sẽ dùng ở bước RAG


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
        "ready",
        page_count=result.page_count,
        extract_method=result.method,
    )
    for warning in result.warnings:
        logger.warning("Tài liệu %d: %s", document_id, warning)
    return PipelineOutcome(
        document_id=document_id,
        chunk_count=len(chunks),
        page_count=result.page_count,
        method=result.method,
        warnings=result.warnings,
    )


def _process_with_retries(job: sqlite3.Row) -> None:
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
        "Tài liệu %s sẵn sàng: %d đoạn, %d trang, cách đọc %s",
        outcome.document_id, outcome.chunk_count, outcome.page_count, outcome.method,
    )


def run_pending_jobs(limit: int = 20) -> int:
    """Xử lý các việc đang chờ. Dùng cho cả nền tảng và lúc khởi động."""
    processed = 0
    for _ in range(limit):
        job = jobs_repo.claim_next(jobs_repo.STAGE_OCR)
        if not job:
            break
        _process_with_retries(job)
        processed += 1
    return processed


def recover_on_startup() -> None:
    """Đưa việc bị kẹt về hàng đợi và xử lý tiếp khi khởi động."""
    requeued = jobs_repo.requeue_stale()
    if requeued:
        logger.info("Đã đưa %d việc bị kẹt trở lại hàng đợi.", requeued)
    run_pending_jobs()


def delete_document_files(document: dict) -> None:
    try:
        storage.delete_stored_file(document["storage_path"])
    except storage.StorageError as exc:
        logger.warning("Không xoá được tệp của tài liệu %s: %s", document.get("id"), exc)
