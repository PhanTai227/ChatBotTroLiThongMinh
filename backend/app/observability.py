"""Cấu hình nhật ký và theo dõi yêu cầu."""

from __future__ import annotations

import logging
import time
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request, Response

from .config import get_settings

ACCESS_LOG = logging.getLogger("mindora.access")

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s | %(message)s"


def configure_logging() -> None:
    """Thiết lập nhật ký ra console và tệp (xoay vòng 2 MB, giữ 3 bản)."""
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if settings.log_to_file:
        log_dir: Path = settings.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    logging.getLogger("uvicorn.access").propagate = False
    ACCESS_LOG.setLevel(settings.log_level)


def new_request_id() -> str:
    return uuid.uuid4().hex[:8]


def register_request_logging(app: FastAPI) -> None:
    """Gắn request_id và ghi một dòng nhật ký cho mỗi yêu cầu."""

    @app.middleware("http")
    async def log_request(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or new_request_id()
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = (time.perf_counter() - started) * 1000
            ACCESS_LOG.warning(
                "%s %s -> lỗi sau %.0f ms | request_id=%s",
                request.method,
                request.url.path,
                elapsed_ms,
                request_id,
            )
            raise
        elapsed_ms = (time.perf_counter() - started) * 1000
        user_id = getattr(request.state, "user_id", None)
        ACCESS_LOG.info(
            "%s %s -> %s | %.0f ms | request_id=%s%s",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
            request_id,
            f" | user_id={user_id}" if user_id else "",
        )
        response.headers["X-Request-ID"] = request_id
        return response
