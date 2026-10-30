-- Lưu phạm vi tài liệu của từng tin nhắn để lịch sử hội thoại không làm lẫn
-- chế độ hỏi tự do với chế độ chỉ trả lời theo tài liệu đã chọn.
ALTER TABLE messages ADD COLUMN document_scope TEXT NOT NULL DEFAULT '[]';

CREATE INDEX IF NOT EXISTS idx_messages_conversation_scope
    ON messages(conversation_id, document_scope, id);
