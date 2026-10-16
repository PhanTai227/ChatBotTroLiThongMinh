"""Điểm khởi tạo ứng dụng FastAPI của Mindora.

Bố cục mã nguồn:
- config.py     : cấu hình từ biến môi trường
- db.py         : kết nối SQLite, transaction, migration
- repositories/ : truy vấn dữ liệu
- services/     : nghiệp vụ và dịch vụ AI
- routers/      : định nghĩa endpoint
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import bootstrap_async
from .config import get_settings
from .errors import register_exception_handlers
from .observability import configure_logging, register_request_logging
from .routers import admin, auth, chat, conversations, documents, feedback, progress

logger = logging.getLogger("mindora.worker")

# Chu kỳ worker xử lý tài liệu nền: đủ nhanh để job thử lại đúng hẹn
# (backoff 5s/30s/120s), đủ thưa để không tốn CPU khi không có việc.
WORKER_INTERVAL_SECONDS = 5.0


async def _document_worker(stop: asyncio.Event) -> None:
    """Vòng lặp nền: xử lý các việc OCR/embedding đang chờ hoặc tới hẹn thử lại.

    Trước đây job chỉ được chạy 1 lần duy nhất lúc upload (qua BackgroundTasks),
    nên khi thất bại tạm thời (Ollama chưa sẵn sàng, timeout...) tài liệu kẹt
    mãi ở 85% cho tới khi restart backend hoặc upload tệp khác. Worker này
    đảm bảo mọi job tới hẹn đều được chạy lại mà không cần người dùng làm gì.
    """
    from .services import documents as documents_service

    while not stop.is_set():
        try:
            await documents_service.run_pending_jobs()
        except Exception:  # noqa: BLE001 - worker nền không được chết vì lỗi lẻ
            logger.exception("Worker xử lý tài liệu gặp lỗi, sẽ thử lại ở chu kỳ sau.")
        try:
            await asyncio.wait_for(stop.wait(), timeout=WORKER_INTERVAL_SECONDS)
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Chuẩn bị cơ sở dữ liệu và nhật ký trước khi phục vụ yêu cầu."""
    configure_logging()
    await bootstrap_async()
    # Trong kiểm thử (pytest), TestClient mở/đóng lifespan liên tục và vòng lặp
    # nền giữ portal của anyio không thoát được -> treo ở khâu teardown.
    # Chỉ chạy worker khi KHÔNG ở trong pytest.
    import os
    import sys

    in_test = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules
    stop = asyncio.Event()
    task = asyncio.create_task(_document_worker(stop)) if not in_test else None
    try:
        yield
    finally:
        if task is not None:
            stop.set()
            try:
                await asyncio.wait_for(task, timeout=10.0)
            except (TimeoutError, asyncio.CancelledError):
                task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_request_logging(application)
    register_exception_handlers(application)
    application.include_router(auth.router)
    application.include_router(admin.router)
    application.include_router(chat.router)
    application.include_router(conversations.router)
    application.include_router(documents.router)
    application.include_router(feedback.router)
    application.include_router(progress.router)
    return application


app = create_app()
