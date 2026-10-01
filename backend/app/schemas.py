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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None

    @field_validator("message")
    @classmethod
    def _message_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("câu hỏi không được để trống hoặc chỉ gõ khoảng trắng")
        return cleaned


class ChatResponse(BaseModel):
    answer: str
    conversation_id: int
    model: str
