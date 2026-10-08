"""Điểm khởi tạo ứng dụng FastAPI của Mindora.

Bố cục mã nguồn:
- config.py     : cấu hình từ biến môi trường
- db.py         : kết nối SQLite, transaction, migration
- repositories/ : truy vấn dữ liệu
- services/     : nghiệp vụ và dịch vụ AI
- routers/      : định nghĩa endpoint
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .bootstrap import bootstrap_async
from .config import get_settings
from .errors import register_exception_handlers
from .observability import configure_logging, register_request_logging
from .routers import admin, auth, chat, conversations, documents, feedback, progress


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Chuẩn bị cơ sở dữ liệu và nhật ký trước khi phục vụ yêu cầu."""
    configure_logging()
    await bootstrap_async()
    yield


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
