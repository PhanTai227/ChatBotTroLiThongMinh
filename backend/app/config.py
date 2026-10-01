"""Cấu hình ứng dụng, đọc từ biến môi trường và tệp backend/.env.

Mọi giá trị đều đọc lười (lazy) ở lần gọi đầu tiên để kiểm thử có thể ghi đè
biến môi trường trước khi khởi tạo ứng dụng.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent

VALID_APP_MODES = ("local", "server")
VALID_LLM_PROVIDERS = ("ollama",)


def _load_dotenv() -> None:
    """Nạp backend/.env nếu có. Không phụ thuộc thư viện ngoài."""
    env_file = BACKEND_DIR / ".env"
    if not env_file.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        for raw_line in env_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return
    load_dotenv(env_file, override=False)


def _str_env(key: str, default: str) -> str:
    value = os.getenv(key)
    return value.strip() if value and value.strip() else default


def _int_env(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{key} phải là số nguyên, nhận được: {raw!r}") from exc


def _float_env(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{key} phải là số thực, nhận được: {raw!r}") from exc


def _bool_env(key: str, default: bool) -> bool:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _list_env(key: str, default: tuple[str, ...]) -> tuple[str, ...]:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Cấu hình đã chuẩn hoá và kiểm tra."""

    app_name: str = "Mindora Local API"
    app_version: str = "0.2.0"
    app_mode: str = "local"

    database_path: Path = field(default_factory=Path)
    db_timeout_seconds: float = 10.0
    busy_timeout_ms: int = 5_000

    llm_provider: str = "ollama"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    model_keep_alive: str = "10m"
    model_temperature: float = 0.25
    model_top_p: float = 0.9
    model_num_predict: int = 600
    # Ollama mặc định dùng cửa sổ ngữ cảnh rất nhỏ, phải chỉ định tường minh khi làm RAG.
    model_num_ctx: int = 8_192
    llm_timeout_seconds: float = 180.0
    health_timeout_seconds: float = 2.0

    session_days: int = 7
    pbkdf2_iterations: int = 310_000
    default_admin_email: str = "admin@mindora.local"
    default_admin_password: str = "Admin@123"
    default_max_upload_mb: int = 20

    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")

    # --- Tài liệu và OCR ---
    # Đường dẫn tesseract.exe; để trống thì tự dò trong các vị trí thông dụng.
    tesseract_cmd: str = ""
    tesseract_lang: str = "vie+eng"
    ocr_dpi: int = 200
    chunk_size: int = 800
    chunk_overlap: int = 120
    max_attempts: int = 3
    allowed_upload_types: tuple[str, ...] = (".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg")

    # --- RAG: vector nhúng và tìm kiếm ngữ nghĩa ---
    # Model embedding chạy cũng qua Ollama nên không thêm phụ thuộc nặng cho máy cục bộ.
    embedding_model: str = "nomic-embed-text"
    # Số chiều của vector. nomic-embed-text = 768, bge-m3 = 1024. Chỉ dùng để kiểm tra
    # khi đọc lại vector đã lưu nên đổi model phải sinh lại vector của các tài liệu cũ.
    embedding_dim: int = 768
    embedding_batch_size: int = 16
    rag_top_k: int = 6
    # Ngưỡng điểm tương đồng: dưới ngưỡng này coi như không có ngữ cảnh để chống ảo giác (NFR-4).
    rag_min_score: float = 0.35
    # Số ký tự của mỗi đoạn được đưa vào ngữ cảnh câu hỏi.
    rag_context_chars: int = 6_000

    log_level: str = "INFO"
    log_to_file: bool = True
    log_dir: Path = field(default_factory=Path)
    storage_dir: Path = field(default_factory=Path)
    upload_tmp_dir: Path = field(default_factory=Path)

    def validate(self) -> None:
        if self.app_mode not in VALID_APP_MODES:
            raise ValueError(f"APP_MODE phải là một trong {VALID_APP_MODES}, nhận được: {self.app_mode!r}")
        if self.llm_provider not in VALID_LLM_PROVIDERS:
            raise ValueError(f"LLM_PROVIDER phải là một trong {VALID_LLM_PROVIDERS}, nhận được: {self.llm_provider!r}")
        if not self.ollama_host.startswith(("http://", "https://")):
            raise ValueError(f"OLLAMA_HOST phải bắt đầu bằng http:// hoặc https://, nhận được: {self.ollama_host!r}")
        if self.model_num_ctx < 2_048:
            raise ValueError("MODEL_NUM_CTX phải từ 2048 trở lên để RAG không bị cắt ngữ cảnh.")
        if self.session_days < 1:
            raise ValueError("SESSION_DAYS phải từ 1 trở lên.")
        if self.chunk_size < 100:
            raise ValueError("CHUNK_SIZE phải từ 100 trỏ lên.")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("CHUNK_OVERLAP phải từ 0 trở lên và nhỏ hơn CHUNK_SIZE.")
        if not self.allowed_upload_types:
            raise ValueError("ALLOWED_UPLOAD_TYPES không được để trống.")
        if self.embedding_dim < 8:
            raise ValueError("EMBEDDING_DIM phải từ 8 trở lên.")
        if self.embedding_batch_size < 1:
            raise ValueError("EMBEDDING_BATCH_SIZE phải từ 1 trở lên.")
        if not 1 <= self.rag_top_k <= 50:
            raise ValueError("RAG_TOP_K phải từ 1 đến 50.")
        if not -1.0 <= self.rag_min_score <= 1.0:
            raise ValueError("RAG_MIN_SCORE phải nằm trong khoảng -1.0 đến 1.0.")
        if self.rag_context_chars < 500:
            raise ValueError("RAG_CONTEXT_CHARS phải từ 500 trở lên.")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    database_value = _str_env("DATABASE_PATH", "learning_assistant.db")
    database_path = Path(database_value)
    if not database_path.is_absolute():
        database_path = APP_DIR / database_path

    settings = Settings(
        app_mode=_str_env("APP_MODE", "local"),
        database_path=database_path,
        db_timeout_seconds=_float_env("DB_TIMEOUT_SECONDS", 10.0),
        busy_timeout_ms=_int_env("DB_BUSY_TIMEOUT_MS", 5_000),
        llm_provider=_str_env("LLM_PROVIDER", "ollama"),
        ollama_host=_str_env("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=_str_env("OLLAMA_MODEL", "qwen2.5:3b"),
        model_keep_alive=_str_env("MODEL_KEEP_ALIVE", "10m"),
        model_temperature=_float_env("MODEL_TEMPERATURE", 0.25),
        model_top_p=_float_env("MODEL_TOP_P", 0.9),
        model_num_predict=_int_env("MODEL_NUM_PREDICT", 600),
        model_num_ctx=_int_env("MODEL_NUM_CTX", 8_192),
        llm_timeout_seconds=_float_env("LLM_TIMEOUT_SECONDS", 180.0),
        health_timeout_seconds=_float_env("HEALTH_TIMEOUT_SECONDS", 2.0),
        session_days=_int_env("SESSION_DAYS", 7),
        pbkdf2_iterations=_int_env("PBKDF2_ITERATIONS", 310_000),
        default_admin_email=_str_env("DEFAULT_ADMIN_EMAIL", "admin@mindora.local"),
        default_admin_password=_str_env("DEFAULT_ADMIN_PASSWORD", "Admin@123"),
        default_max_upload_mb=_int_env("DEFAULT_MAX_UPLOAD_MB", 20),
        cors_origins=_list_env("CORS_ORIGINS", ("http://127.0.0.1:5173", "http://localhost:5173")),
        tesseract_cmd=_str_env("TESSERACT_CMD", ""),
        tesseract_lang=_str_env("TESSERACT_LANG", "vie+eng"),
        ocr_dpi=_int_env("OCR_DPI", 200),
        chunk_size=_int_env("CHUNK_SIZE", 800),
        chunk_overlap=_int_env("CHUNK_OVERLAP", 120),
        max_attempts=_int_env("MAX_ATTEMPTS", 3),
        embedding_model=_str_env("EMBEDDING_MODEL", "nomic-embed-text"),
        embedding_dim=_int_env("EMBEDDING_DIM", 768),
        embedding_batch_size=_int_env("EMBEDDING_BATCH_SIZE", 16),
        rag_top_k=_int_env("RAG_TOP_K", 6),
        rag_min_score=_float_env("RAG_MIN_SCORE", 0.35),
        rag_context_chars=_int_env("RAG_CONTEXT_CHARS", 6_000),
        allowed_upload_types=_list_env(
            "ALLOWED_UPLOAD_TYPES", (".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg")
        ),
        log_level=_str_env("LOG_LEVEL", "INFO").upper(),
        log_to_file=_bool_env("LOG_TO_FILE", True),
        log_dir=Path(_str_env("LOG_DIR", str(BACKEND_DIR / "logs"))),
        storage_dir=Path(_str_env("STORAGE_DIR", str(APP_DIR / "storage"))),
        upload_tmp_dir=Path(_str_env("UPLOAD_TMP_DIR", str(APP_DIR / "storage" / "tmp"))),
    )
    settings.validate()
    return settings


def reset_settings_cache() -> None:
    """Xoá cache cấu hình, dùng trong kiểm thử."""
    get_settings.cache_clear()

