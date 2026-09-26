from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "learning_assistant.db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
SESSION_DAYS = 7
PBKDF2_ITERATIONS = 310_000
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@mindora.local")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")

SYSTEM_PROMPT = """Bạn là trợ lý học tập AI của hệ thống Mindora.
Hãy trả lời bằng tiếng Việt, rõ ràng, chính xác và thân thiện.
Nếu câu hỏi cần thông tin chưa được cung cấp, hãy nói rõ bạn chưa đủ thông tin thay vì bịa.
Với bài toán hoặc bài tập, trình bày từng bước và không chỉ đưa đáp án.
Giữ câu trả lời vừa phải để phù hợp với giao diện web."""


def init_database() -> None:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('user', 'admin')),
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action TEXT NOT NULL,
                target_user_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(admin_id) REFERENCES users(id),
                FOREIGN KEY(target_user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT NOT NULL DEFAULT 'Cuộc hội thoại mới',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );
            """
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(conversations)")}
        if "user_id" not in columns:
            connection.execute("ALTER TABLE conversations ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
        if not connection.execute("SELECT 1 FROM users LIMIT 1").fetchone():
            connection.execute(
                "INSERT INTO users(full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                ("Quản trị viên", DEFAULT_ADMIN_EMAIL, hash_password(DEFAULT_ADMIN_PASSWORD)),
            )
        admin_id = connection.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1").fetchone()[0]
        connection.execute("UPDATE conversations SET user_id = ? WHERE user_id IS NULL", (admin_id,))
        connection.executemany(
            "INSERT OR IGNORE INTO system_settings(key, value) VALUES (?, ?)",
            [("max_upload_mb", "20"), ("ai_model", OLLAMA_MODEL)],
        )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$")
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return algorithm == "pbkdf2_sha256" and secrets.compare_digest(actual.hex(), digest_hex)
    except (TypeError, ValueError):
        return False


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(48)
    expires_at = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).isoformat()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("INSERT INTO sessions(token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires_at))
    return token


def current_user(authorization: str | None) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bạn cần đăng nhập.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """SELECT u.id, u.full_name, u.email, u.role, u.is_active
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > ?""",
            (authorization.removeprefix("Bearer ").strip(), datetime.now(timezone.utc).isoformat()),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Phiên đăng nhập đã hết hạn.")
    if not row["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa.")
    return dict(row)


def require_admin(user: dict) -> None:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ quản trị viên được phép thực hiện.")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title="Mindora Local API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: int
    model: str


@app.post("/api/auth/register")
async def register(request: AuthRequest) -> dict:
    email = request.email.strip().lower()
    with sqlite3.connect(DATABASE_PATH) as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO users(full_name, email, password_hash) VALUES (?, ?, ?)",
                (request.full_name.strip(), email, hash_password(request.password)),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=409, detail="Email đã được sử dụng.") from exc
        user_id = int(cursor.lastrowid)
    return {"token": create_session(user_id), "user": {"id": user_id, "full_name": request.full_name.strip(), "email": email, "role": "user"}}


@app.post("/api/auth/login")
async def login(request: LoginRequest) -> dict:
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        user = connection.execute("SELECT * FROM users WHERE email = ?", (request.email.strip().lower(),)).fetchone()
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng.")
    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = ?", (user["id"],))
    return {"token": create_session(int(user["id"])), "user": {"id": user["id"], "full_name": user["full_name"], "email": user["email"], "role": user["role"]}}


@app.get("/api/auth/me")
async def me(authorization: str | None = Header(default=None)) -> dict:
    return {"user": current_user(authorization)}


@app.post("/api/auth/logout")
async def logout(authorization: str | None = Header(default=None)) -> dict:
    current_user(authorization)
    token = authorization.removeprefix("Bearer ").strip()
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
    return {"message": "Đã đăng xuất"}


@app.get("/api/admin/users")
async def admin_users(authorization: str | None = Header(default=None)) -> list[dict]:
    admin = current_user(authorization)
    require_admin(admin)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        users = connection.execute("SELECT id, full_name, email, role, is_active, created_at, last_login_at FROM users ORDER BY created_at DESC").fetchall()
    return [dict(user) for user in users]


@app.patch("/api/admin/users")
async def update_user(request: UserActionRequest, authorization: str | None = Header(default=None)) -> dict:
    admin = current_user(authorization)
    require_admin(admin)
    if request.user_id == admin["id"] and request.is_active is False:
        raise HTTPException(status_code=400, detail="Không thể tự khóa tài khoản Admin đang đăng nhập.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        if request.role is not None:
            if request.role not in {"user", "admin"}:
                raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
            if request.user_id == admin["id"] and request.role != "admin":
                raise HTTPException(status_code=400, detail="Không thể tự hạ quyền tài khoản đang đăng nhập.")
            connection.execute("UPDATE users SET role = ? WHERE id = ?", (request.role, request.user_id))
        if request.is_active is not None:
            connection.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(request.is_active), request.user_id))
            if not request.is_active:
                connection.execute("DELETE FROM sessions WHERE user_id = ?", (request.user_id,))
        if request.new_password:
            connection.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(request.new_password), request.user_id))
            connection.execute("DELETE FROM sessions WHERE user_id = ?", (request.user_id,))
        connection.execute("INSERT INTO audit_logs(admin_id, action, target_user_id) VALUES (?, ?, ?)", (admin["id"], "update_user", request.user_id))
    return {"message": "Đã cập nhật người dùng"}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, authorization: str | None = Header(default=None)) -> dict:
    admin = current_user(authorization)
    require_admin(admin)
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Không thể xóa tài khoản Admin đang đăng nhập.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))
        connection.execute("INSERT INTO audit_logs(admin_id, action, target_user_id) VALUES (?, 'delete_user', ?)", (admin["id"], user_id))
    return {"message": "Đã xóa người dùng"}


@app.get("/api/admin/settings")
async def admin_settings(authorization: str | None = Header(default=None)) -> list[dict]:
    admin = current_user(authorization)
    require_admin(admin)
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.row_factory = sqlite3.Row
        settings = connection.execute("SELECT key, value, updated_at FROM system_settings ORDER BY key").fetchall()
    return [dict(setting) for setting in settings]


@app.patch("/api/admin/settings/{setting_key}")
async def update_setting(setting_key: str, request: SettingRequest, authorization: str | None = Header(default=None)) -> dict:
    admin = current_user(authorization)
    require_admin(admin)
    if setting_key not in {"max_upload_mb", "ai_model"}:
        raise HTTPException(status_code=404, detail="Không tìm thấy cấu hình.")
    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("UPDATE system_settings SET value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?", (request.value, setting_key))
        connection.execute("INSERT INTO audit_logs(admin_id, action) VALUES (?, 'update_setting')", (admin["id"],))
    return {"message": "Đã cập nhật cấu hình"}


@app.get("/api/admin/stats")
async def admin_stats(authorization: str | None = Header(default=None)) -> dict:
    admin = current_user(authorization)
    require_admin(admin)
    with sqlite3.connect(DATABASE_PATH) as connection:
        return {
            "users": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
            "active_users": connection.execute("SELECT COUNT(*) FROM users WHERE is_active = 1").fetchone()[0],
            "conversations": connection.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "questions": connection.execute("SELECT COUNT(*) FROM messages WHERE role = 'user'").fetchone()[0],
        }

@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
            return {"status": "ok", "ollama": "connected", "model": OLLAMA_MODEL}
    except httpx.HTTPError:
        return {"status": "degraded", "ollama": "unavailable", "model": OLLAMA_MODEL}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: str | None = Header(default=None)) -> ChatResponse:
    user = current_user(authorization)
    with sqlite3.connect(DATABASE_PATH) as connection:
        if request.conversation_id is None:
            cursor = connection.execute(
                "INSERT INTO conversations(user_id, title) VALUES (?, ?)",
                (user["id"], request.message.strip()[:60]),
            )
            conversation_id = int(cursor.lastrowid)
        else:
            conversation_id = request.conversation_id
            exists = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND (user_id = ? OR user_id IS NULL)",
                (conversation_id, user["id"]),
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Không tìm thấy cuộc hội thoại.")

        connection.execute(
            "INSERT INTO messages(conversation_id, role, content) VALUES (?, 'user', ?)",
            (conversation_id, request.message.strip()),
        )

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": request.message.strip()},
                    ],
                    "stream": False,
                    "keep_alive": "10m",
                    "options": {
                        "temperature": 0.25,
                        "top_p": 0.9,
                        "num_predict": 600,
                    },
                },
            )
            response.raise_for_status()
            answer = response.json().get("message", {}).get("content", "").strip()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="AI local phản hồi quá lâu. Hãy thử câu ngắn hơn.") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail="Không kết nối được Ollama. Hãy kiểm tra Ollama và model đã tải.",
        ) from exc

    if not answer:
        raise HTTPException(status_code=502, detail="AI local không trả về nội dung.")

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "INSERT INTO messages(conversation_id, role, content) VALUES (?, 'assistant', ?)",
            (conversation_id, answer),
        )

    return ChatResponse(answer=answer, conversation_id=conversation_id, model=OLLAMA_MODEL)
