"""Chia văn bản thành các đoạn nhỏ phục vụ tìm kiếm ngữ nghĩa (RAG).

Thuật toán: giữ nguyên ranh giới câu/đoạn văn bản, ghép cho tới khi đạt kích thước
mục tiêu rồi lùi lại `overlap` ký tự để không mất ngữ cảnh giữa hai đoạn.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Dấu kết thúc câu, gồm cả dấu ba chấm và dấu gạch dài.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+|\n{2,}")
_WHITESPACE = re.compile(r"[ \t\x0b\f\r]+")


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    page_number: int | None
    token_estimate: int


def normalize(text: str) -> str:
    """Gộp khoảng trắng thừa nhưng giữ ngắt dòng làm ranh giới đoạn."""
    lines = [_WHITESPACE.sub(" ", line).strip() for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)


def _split_units(text: str) -> list[str]:
    """Tách thành các đơn vị nhỏ: câu trước, câu sau là dấu xuống dòng."""
    units: list[str] = []
    for block in text.split("\n"):
        for piece in _SENTENCE_SPLIT.split(block):
            cleaned = piece.strip()
            if cleaned:
                units.append(cleaned)
    return units


def _hard_split(text: str, size: int) -> list[str]:
    return [text[start : start + size] for start in range(0, len(text), size)]


def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Chia một đoạn văn bản thuần thành các đoạn nhỏ có phần chồng lấn."""
    cleaned = normalize(text)
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    chunks: list[str] = []
    buffer = ""
    for unit in _split_units(cleaned):
        for piece in _hard_split(unit, chunk_size) if len(unit) > chunk_size else [unit]:
            if buffer and len(buffer) + len(piece) + 1 > chunk_size:
                chunks.append(buffer)
                buffer = buffer[-overlap:] if overlap else ""
            buffer = f"{buffer} {piece}".strip() if buffer else piece
    if buffer.strip():
        chunks.append(buffer)
    return [chunk for chunk in chunks if chunk.strip()]


def split_pages(
    pages: list[tuple[int | None, str]],
    chunk_size: int,
    overlap: int,
) -> list[TextChunk]:
    """Chia nhiều trang thành đoạn, giữ lại số trang để làm căn cứ trích dẫn."""
    chunks: list[TextChunk] = []
    for page_number, page_text in pages:
        for piece in split_text(page_text, chunk_size, overlap):
            if not piece.strip():
                continue
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=piece,
                    page_number=page_number,
                    # Ước lượng ~4 ký tự cho mỗi token, đủ để cảnh báo khi quá dài.
                    token_estimate=max(1, len(piece) // 4),
                )
            )
    return chunks


def estimate_tokens(text: str) -> int:
    return max(1, len(text or "") // 4)
