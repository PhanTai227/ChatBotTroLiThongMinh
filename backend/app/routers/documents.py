"""Endpoint quản lý tài liệu: tải lên, xem, gắn nhãn, xoá, tải tệp gốc."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse

from ..config import get_settings
from ..deps import get_current_user
from ..repositories import chunks as chunks_repo
from ..repositories import documents as documents_repo
from ..repositories import jobs as jobs_repo
from ..repositories import settings_repo
from ..repositories import summaries as summaries_repo
from ..schemas import DocumentUpdate
from ..services import documents as documents_service
from ..services import storage
from ..services import summaries as summaries_service
from ..services.llm import LLMEmptyResponse, LLMModelMissing, LLMTimeout, LLMUnavailable

logger = logging.getLogger("mindora.api.documents")
router = APIRouter(prefix="/api/documents", tags=["Tài liệu"])

READ_BLOCK = 1024 * 1024


def _max_upload_mb() -> int:
    return settings_repo.get_int("max_upload_mb", get_settings().default_max_upload_mb)


def _owned_document(document_id: int, owner_id: int) -> dict:
    row = documents_repo.get_owned(document_id, owner_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài liệu.")
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_tag: str | None = Form(default=None),
    chapter_tag: str | None = Form(default=None),
    authorization: str | None = Header(default=None),
) -> dict:
    """Tải tệp lên, kiểm tra định dạng/dung lượng, lưu vào hàng đợi xử lý nền."""
    user = get_current_user(request, authorization)

    async def blocks() -> AsyncIterator[bytes]:
        while True:
            block = await file.read(READ_BLOCK)
            if not block:
                break
            yield block

    try:
        stored = await storage.store_stream(blocks(), file.filename or "", _max_upload_mb())
    except storage.UploadTooLarge as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    except storage.UnsupportedFile as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except storage.StorageError as exc:
        logger.exception("Lỗi lưu trữ khi tải tệp lên")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Không lưu được tệp tải lên."
        ) from exc

    existing = documents_repo.find_by_hash(int(user["id"]), stored.content_hash)
    if existing:
        storage.delete_stored_file(stored.relative_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tệp này đã được tải lên (mã tài liệu {existing['id']}).",
        )

    document_id = documents_repo.create_document(
        owner_id=int(user["id"]),
        file_name=(file.filename or f"tai-lieu{stored.extension}")[:255],
        file_type=stored.file_type,
        storage_path=stored.relative_path,
        content_hash=stored.content_hash,
        subject_tag=subject_tag or None,
        chapter_tag=chapter_tag or None,
        mime_type=file.content_type,
    )
    moved = storage.move_to_document_folder(stored, int(user["id"]), document_id)
    documents_repo.set_storage(document_id, moved.relative_path, moved.size_kb)
    jobs_repo.enqueue(document_id, jobs_repo.STAGE_OCR)
    background_tasks.add_task(documents_service.run_pending_jobs)
    return _owned_document(document_id, int(user["id"]))


@router.get("")
async def list_documents(
    request: Request,
    authorization: str | None = Header(default=None),
    subject_tag: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Tìm theo tên tệp hoặc chương"),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    user = get_current_user(request, authorization)
    items = documents_repo.list_for_owner(
        int(user["id"]), subject_tag=subject_tag, search=q, status=status_filter, limit=limit, offset=offset
    )
    return {
        "items": items,
        "total": documents_repo.count_for_owner(
            int(user["id"]), subject_tag=subject_tag, search=q, status=status_filter
        ),
        "total_all": documents_repo.count_for_owner(int(user["id"])),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    user = get_current_user(request, authorization)
    document = _owned_document(document_id, int(user["id"]))
    document["chunk_count"] = chunks_repo.count_for_document(document_id)
    return document


@router.get("/{document_id}/status")
async def document_status(
    document_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    """Giao diện gọi định kỳ để theo dõi tiến trình xử lý tài liệu."""
    user = get_current_user(request, authorization)
    document = _owned_document(document_id, int(user["id"]))
    return {
        "id": document["id"],
        "status": document["status"],
        "error_message": document["error_message"],
        "page_count": document["page_count"],
        "extract_method": document["extract_method"],
        "chunk_count": chunks_repo.count_for_document(document_id),
    }


@router.patch("/{document_id}")
async def update_document(
    document_id: int,
    payload: DocumentUpdate,
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    user = get_current_user(request, authorization)
    _owned_document(document_id, int(user["id"]))
    documents_repo.update_metadata(
        document_id,
        file_name=payload.file_name,
        subject_tag=payload.subject_tag,
        chapter_tag=payload.chapter_tag,
    )
    return _owned_document(document_id, int(user["id"]))


@router.get("/{document_id}/download")
async def download_document(
    document_id: int, request: Request, authorization: str | None = Header(default=None)
) -> FileResponse:
    user = get_current_user(request, authorization)
    document = _owned_document(document_id, int(user["id"]))
    try:
        path = storage.resolve_stored_path(document["storage_path"])
    except storage.StorageError as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp trên đĩa.") from exc
    if not path.exists():
        raise HTTPException(status_code=404, detail="Tệp tài liệu không còn trên đĩa.")
    return FileResponse(path=path, filename=document["file_name"], media_type=document["mime_type"])


@router.get("/{document_id}/chunks")
async def document_chunks(
    document_id: int,
    request: Request,
    authorization: str | None = Header(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Xem các đoạn đã trích xuất, hữu ích khi kiểm tra chất lượng RAG."""
    user = get_current_user(request, authorization)
    _owned_document(document_id, int(user["id"]))
    items = chunks_repo.list_for_document(document_id, limit=limit, offset=offset)
    return {"items": items, "total": chunks_repo.count_for_document(document_id)}


@router.get("/{document_id}/summary")
async def document_summary(
    document_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    """Tóm tắt tài liệu (Module C, FR-B5). Sinh một lần rồi lưu để chỉ tốn một lượt LLM."""
    user = get_current_user(request, authorization)
    document = _owned_document(document_id, int(user["id"]))
    if document["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tài liệu chưa sẵn sàng để tóm tắt. Hãy chờ xử lý xong rồi thử lại.",
        )
    cached = summaries_repo.get_cached(document_id, "document")
    if cached:
        return {**cached, "cached": True}
    try:
        content = await summaries_service.generate_summary(document_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Tài liệu không có nội dung để tóm tắt."
        ) from exc
    except LLMTimeout as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI tóm tắt tài liệu quá lâu. Hãy thử lại sau.",
        ) from exc
    except (LLMModelMissing, LLMUnavailable) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không kết nối được AI để tóm tắt tài liệu.",
        ) from exc
    except LLMEmptyResponse as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="AI không trả về nội dung tóm tắt."
        ) from exc
    saved = summaries_repo.save(document_id, content, "document")
    return {**saved, "cached": False}


@router.delete("/{document_id}")
async def delete_document(
    document_id: int, request: Request, authorization: str | None = Header(default=None)
) -> dict:
    user = get_current_user(request, authorization)
    document = _owned_document(document_id, int(user["id"]))
    documents_repo.delete_document(document_id)
    documents_service.delete_document_files(document)
    return {"message": "Đã xoá tài liệu"}
