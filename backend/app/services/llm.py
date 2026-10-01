"""Dịch vụ AI: điểm duy nhất trong hệ thống được phép biết chi tiết về LLM.

Router chỉ gọi `get_provider()` và `resolve_model()`, nhờ vậy sau này thay Ollama
bằng dịch vụ khác (Gemini, OpenAI...) chỉ cần viết thêm một lớp, không đụng
tới mã nghiệp vụ.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

import httpx

from ..config import get_settings
from ..repositories import settings_repo

logger = logging.getLogger("mindora.llm")

SYSTEM_PROMPT = """Bạn là trợ lý học tập AI của hệ thống Mindora.
Hãy trả lời bằng tiếng Việt, rõ ràng, chính xác và thân thiện.
Nếu câu hỏi cần thông tin chưa được cung cấp, hãy nói rõ bạn chưa đủ thông tin thay vì bịa.
Với bài toán hoặc bài tập, trình bày từng bước và không chỉ đưa đáp án.
Giữ câu trả lời vừa phải để phù hợp với giao diện web."""

# Câu dẫn khi có ngữ cảnh lấy từ tài liệu: bắt buộc bám theo ngữ cảnh và trích dẫn nguồn.
RAG_SYSTEM_PROMPT = """Bạn là trợ lý học tập AI của hệ thống Mindora.
Bạn được cung cấp các trích đoạn từ tài liệu của người dùng, mỗi trích đoạn có số thứ tự [1], [2]...
Hãy trả lời câu hỏi DỰA TRÊN CHÍNH CÁC TRÍCH ĐOẠN ĐÓ:
- Chỉ dùng thông tin có trong ngữ cảnh; tuyệt đối không bịa hay bổ sung từ kiến thức ngoài.
- Nếu ngữ cảnh không đủ để trả lời, nói rõ là chưa đủ thông tin trong tài liệu.
- Mỗi ý chính phải kèm số nguồn dạng [1], [2] đúng với trích đoạn đã dùng.
- Trả lời bằng tiếng Việt, rõ ràng, ngắn gọn, hợp với giao diện web."""

# Câu trả lời khi tìm không ra ngữ cảnh đủ tin cậy: nói thẳng thay vì đoán (NFR-4).
NO_CONTEXT_ANSWER = (
    "Tôi chưa tìm thấy phần tài liệu nào liên quan đủ để trả lời câu hỏi này. "
    "Bạn có thể tải thêm tài liệu, đặt câu hỏi khái quát hơn, "
    "hoặc hỏi trực tiếp môn học ở mục Bài tập & Quiz."
)

_MODEL_CACHE_TTL_SECONDS = 60.0
_CONNECT_ATTEMPTS = 2


class LLMError(Exception):
    """Lỗi chung của dịch vụ AI."""


class LLMUnavailable(LLMError):
    """Không kết nối được tới máy chủ AI."""


class LLMTimeout(LLMError):
    """Máy chủ AI phản hồi quá lâu."""


class LLMModelMissing(LLMError):
    """Máy chủ AI chạy nhưng không có model được yêu cầu."""


class LLMEmptyResponse(LLMError):
    """Máy chủ AI trả về nội dung rỗng."""


@dataclass(frozen=True)
class LLMResult:
    content: str
    model: str


class OllamaProvider:
    """Cung cấp LLM cục bộ qua Ollama."""

    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.ollama_host
        self._timeout = httpx.Timeout(settings.llm_timeout_seconds, connect=10.0)
        self._health_timeout = httpx.Timeout(settings.health_timeout_seconds, connect=2.0)
        self._keep_alive = settings.model_keep_alive
        self._temperature = settings.model_temperature
        self._top_p = settings.model_top_p
        self._num_predict = settings.model_num_predict
        self._num_ctx = settings.model_num_ctx

    async def generate(self, messages: list[dict[str, str]], model: str) -> LLMResult:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "keep_alive": self._keep_alive,
            "options": {
                "temperature": self._temperature,
                "top_p": self._top_p,
                "num_predict": self._num_predict,
                "num_ctx": self._num_ctx,
            },
        }
        response = await self._post(f"{self._host}/api/chat", payload, self._timeout)
        if response.status_code == 404:
            raise LLMModelMissing(f"Ollama không có model {model!r}.")
        if response.status_code >= 400:
            raise LLMUnavailable(f"Ollama trả về mã lỗi {response.status_code}.")
        try:
            content = response.json().get("message", {}).get("content", "").strip()
        except ValueError as exc:
            raise LLMUnavailable("Ollama trả về dữ liệu không hợp lệ.") from exc
        if not content:
            raise LLMEmptyResponse("Ollama trả về nội dung rỗng.")
        return LLMResult(content=content, model=model)

    async def list_models(self) -> list[str]:
        response = await self._get(f"{self._host}/api/tags", self._health_timeout)
        if response.status_code >= 400:
            raise LLMUnavailable(f"Ollama trả về mã lỗi {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise LLMUnavailable("Ollama trả về dữ liệu không hợp lệ.") from exc
        return [str(item.get("name", "")) for item in payload.get("models", [])]

    async def version(self) -> str | None:
        try:
            response = await self._get(f"{self._host}/api/version", self._health_timeout)
            return str(response.json().get("version", "")) or None
        except (LLMError, ValueError):
            return None

    async def _get(self, url: str, timeout: httpx.Timeout) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                return await client.get(url)
        except httpx.TimeoutException as exc:
            raise LLMUnavailable("Máy chủ AI không phản hồi.") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable("Không kết nối được máy chủ AI.") from exc

    async def _post(self, url: str, payload: dict, timeout: httpx.Timeout) -> httpx.Response:
        last_error: httpx.HTTPError | None = None
        for attempt in range(1, _CONNECT_ATTEMPTS + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    return await client.post(url, json=payload)
            except httpx.TimeoutException as exc:
                raise LLMTimeout("Máy chủ AI phản hồi quá lâu.") from exc
            except httpx.ConnectError as exc:
                # Máy chủ AI có thể đang khởi động: thử lại một lần trước khi báo lỗi.
                last_error = exc
                if attempt < _CONNECT_ATTEMPTS:
                    await asyncio.sleep(1.0)
            except httpx.HTTPError as exc:
                raise LLMUnavailable("Không kết nối được máy chủ AI.") from exc
        raise LLMUnavailable("Không kết nối được máy chủ AI.") from last_error


_provider: OllamaProvider | None = None
_model_cache: tuple[float, str] | None = None


def get_provider() -> OllamaProvider:
    """Trả về provider đang dùng (khởi tạo một lần cho cả tiến trình)."""
    global _provider
    if _provider is None:
        _provider = OllamaProvider()
    return _provider


async def resolve_model() -> str:
    """Model cần dùng: ưu tiên giá trị admin đặt trong system_settings, đệm 60 giây."""
    global _model_cache
    settings = get_settings()
    now = time.monotonic()
    if _model_cache and now - _model_cache[0] < _MODEL_CACHE_TTL_SECONDS:
        return _model_cache[1]
    model = settings_repo.get_value("ai_model", settings.ollama_model) or settings.ollama_model
    _model_cache = (now, model)
    return model


def invalidate_caches() -> None:
    """Xoá cache của dịch vụ AI, dùng khi cấu hình thay đổi hoặc trong kiểm thử."""
    global _provider, _model_cache
    _provider = None
    _model_cache = None

