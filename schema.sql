-- Hệ thống Trợ lý ảo thông minh khai thác tài liệu và hỗ trợ học tập
-- Cơ sở dữ liệu: SQLite
-- Script idempotent: có thể chạy lại trên database đã khởi tạo.
-- Vector embedding tiếp tục được lưu riêng trong FAISS/Chroma; SQLite chỉ lưu vector_ref.

PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY DEFAULT (
        lower(hex(randomblob(4))) || '-' ||
        lower(hex(randomblob(2))) || '-' || '4' ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    ),
    full_name TEXT NOT NULL CHECK (length(trim(full_name)) BETWEEN 1 AND 150),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE
        CHECK (length(trim(email)) BETWEEN 4 AND 150 AND instr(email, '@') > 1),
    password_hash TEXT NOT NULL CHECK (length(password_hash) >= 20),
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    last_login_at TEXT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY DEFAULT (
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || '4' ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    ),
    owner_id TEXT NOT NULL,
    file_name TEXT NOT NULL CHECK (length(trim(file_name)) BETWEEN 1 AND 255),
    file_type TEXT NOT NULL
        CHECK (file_type IN ('pdf', 'docx', 'xlsx', 'image')),
    mime_type TEXT,
    storage_path TEXT NOT NULL,
    content_hash TEXT,
    subject_tag TEXT CHECK (subject_tag IS NULL OR length(subject_tag) <= 100),
    chapter_tag TEXT CHECK (chapter_tag IS NULL OR length(chapter_tag) <= 150),
    status TEXT NOT NULL DEFAULT 'uploading'
        CHECK (status IN ('uploading', 'ocr_processing', 'embedding', 'ready', 'error')),
    error_message TEXT,
    file_size_kb INTEGER CHECK (file_size_kb IS NULL OR file_size_kb >= 0),
    uploaded_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY DEFAULT (
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || '4' ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    ),
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    vector_ref TEXT,
    page_number INTEGER CHECK (page_number IS NULL OR page_number >= 1),
    UNIQUE (document_id, chunk_index),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS document_summaries (
    id TEXT PRIMARY KEY DEFAULT (
        lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-' || '4' ||
        substr(lower(hex(randomblob(2))), 2) || '-' ||
        substr('89ab', 1, 1) || substr(lower(hex(randomblob(2))), 2) || '-' ||
        lower(hex(randomblob(6)))
    ),
    document_id TEXT NOT NULL,
    summary_type TEXT NOT NULL DEFAULT 'chapter'
        CHECK (summary_type IN ('document', 'chapter', 'custom')),
    target_label TEXT,
    content TEXT NOT NULL CHECK (length(trim(content)) > 0),
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
