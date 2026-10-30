"""Lược đồ dữ liệu đầu vào và đầu ra (Pydantic v2)."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AuthRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name", "email")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("không được để trống hoặc chỉ gõ khoảng trắng")
        return cleaned


class LoginRequest(BaseModel):
    email: str
    password: str


class UserActionRequest(BaseModel):
    user_id: int
    role: str | None = None
    is_active: bool | None = None
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class SettingRequest(BaseModel):
    value: str = Field(min_length=1, max_length=100)


class DocumentUpdate(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    subject_tag: str | None = Field(default=None, max_length=100)
    chapter_tag: str | None = Field(default=None, max_length=150)


class Citation(BaseModel):
    """Nguồn trích dẫn cho câu trả lời, từ đoạn tài liệu tìm được."""

    document_id: int
    chunk_id: int
    file_name: str
    page_number: int | None = None
    snippet: str
    score: float


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    # Tương thích ngược với client cũ chỉ chọn một tài liệu.
    document_id: int | None = None
    # Có phần tử thì chat chỉ được trả lời từ các tài liệu này. Rỗng là chế độ hỏi tự do.
    document_ids: list[int] = Field(default_factory=list, max_length=20)

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("câu hỏi không được để trống hoặc chỉ gõ khoảng trắng")
        return cleaned

    @field_validator("document_ids")
    @classmethod
    def _document_ids_valid(cls, values: list[int]) -> list[int]:
        if any(value < 1 for value in values):
            raise ValueError("mỗi tài liệu phải có mã hợp lệ")
        return list(dict.fromkeys(values))


class ChatResponse(BaseModel):
    answer: str
    conversation_id: int
    model: str
    # Rỗng khi câu trả lời không dựa trên ngữ cảnh tài liệu nào (chống ảo giác NFR-4).
    citations: list[Citation] = Field(default_factory=list)
    # True khi câu trả lời có dùng ngữ cảnh trích từ tài liệu của người dùng.
    used_documents: bool = False


class FeedbackCreate(BaseModel):
    """Phản hồi / đánh giá của học viên gửi tới quản trị viên."""

    rating: int = Field(ge=1, le=5)
    category: str = "other"
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("category")
    @classmethod
    def _category_valid(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"bug", "suggestion", "praise", "other"}:
            raise ValueError("category phải là bug, suggestion, praise hoặc other")
        return cleaned

    @field_validator("content")
    @classmethod
    def _content_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("nội dung phản hồi không được để trống")
        return cleaned


class MessageFeedbackRequest(BaseModel):
    rating: int = Field(description="1 là thích, -1 là không thích")

    @field_validator("rating")
    @classmethod
    def _message_rating_valid(cls, value: int) -> int:
        if value not in {-1, 1}:
            raise ValueError("rating phải là 1 hoặc -1")
        return value

class FeedbackReply(BaseModel):
    """Quản trị viên trả lời một phản hồi."""

    admin_reply: str = Field(min_length=1, max_length=2000)

    @field_validator("admin_reply")
    @classmethod
    def _reply_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("nội dung trả lời không được để trống")
        return cleaned
