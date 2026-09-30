"""Định dạng phản hồi lỗi thống nhất cho toàn bộ API.

Mọi lỗi trả về đều có ba trường: `detail` (thông báo tiếng Việt cho người dùng),
`code` (mã lỗi ổn định để frontend xử lý) và `request_id` (để tra cứu nhật ký).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("mindora.error")

ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    502: "ai_bad_gateway",
    503: "ai_unavailable",
    504: "ai_timeout",
}


def code_for(status_code: int) -> str:
    return ERROR_CODES.get(status_code, "error")


def error_body(detail: str, status_code: int, request: Request) -> dict[str, Any]:
    return {
        "detail": detail,
        "code": code_for(status_code),
        "request_id": getattr(request.state, "request_id", None),
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Yêu cầu không hợp lệ."
        return JSONResponse(status_code=exc.status_code, content=error_body(detail, exc.status_code, request))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [
            {"field": ".".join(str(part) for part in error.get("loc", ())[1:]), "message": error.get("msg", "")}
            for error in exc.errors()
        ]
        body = error_body("Dữ liệu gửi lên không hợp lệ.", 422, request)
        body["fields"] = fields
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Lỗi không lường trước tại %s %s", request.method, request.url.path, exc_info=exc
        )
        return JSONResponse(status_code=500, content=error_body("Lỗi hệ thống. Vui lòng thử lại.", 500, request))
