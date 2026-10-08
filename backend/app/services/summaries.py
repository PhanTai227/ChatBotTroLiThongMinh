"""Tóm tắt tài liệu bằng LLM (Module C, FR-B5).

Tóm tắt được sinh theo yêu cầu rồi lưu vào document_summaries để chỉ tốn
một lượt LLM cho mỗi tài liệu.
"""

from __future__ import annotations

import logging

from ..config import get_settings
from . import documents as documents_service
from .llm import get_provider, resolve_model

logger = logging.getLogger("mindora.summary")

# Tóm tắt 5-8 gạch đầu dòng nằm thoải mái trong giới hạn 600 token của hệ thống.
SUMMARY_NUM_PREDICT = 700

SUMMARY_SYSTEM_PROMPT = """Bạn là trợ lý học tập của hệ thống Mindora.
Hãy tóm tắt trích đoạn tài liệu được cung cấp:
- 5 đến 8 gạch đầu dòng tiếng Việt, mỗi dòng nêu một ý chính.
- Giữ nguyên thuật ngữ quan trọng, không bổ sung kiến thức ngoài tài liệu.
- Chỉ trả về phần tóm tắt, không giải thích hay mở đầu."""


async def generate_summary(document_id: int) -> str:
    """Sinh tóm tắt một tài liệu đã có nội dung. Ném LLMError khi AI gặp sự cố."""
    settings = get_settings()
    context = documents_service.build_document_context(document_id, settings.rag_context_chars)
    if not context:
        raise ValueError("tài liệu không có nội dung để tóm tắt")
    model = await resolve_model()
    result = await get_provider().generate(
        [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": f"TRÍCH ĐOẠN TÀI LIỆU:\n{context}"},
        ],
        model,
        num_predict=SUMMARY_NUM_PREDICT,
    )
    logger.info("Đã tóm tắt tài liệu %s.", document_id)
    return result.content.strip()
