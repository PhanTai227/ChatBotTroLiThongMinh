export type User = {
  id: number;
  full_name: string;
  email: string;
  role: 'user' | 'admin';
  is_active?: number;
};

export type AuthResponse = {
  token: string;
  user: User;
};

const TOKEN_KEY = 'mindora_token';
const API_BASE = 'http://127.0.0.1:8000';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (options.body) headers.set('Content-Type', 'application/json');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Không thể kết nối máy chủ.');
  return data as T;
}

/**
 * Gửi yêu cầu dạng multipart/form-data (tải tài liệu lên).
 * Không tự đặt Content-Type để trình duyệt tự gắn kèm ranh giới multipart.
 */
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const token = getToken();
  const headers = new Headers();
  if (token) headers.set('Authorization', `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, { method: 'POST', headers, body: form });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Không thể kết nối máy chủ.');
  return data as T;
}

export type DocumentItem = {
  id: number;
  file_name: string;
  file_type: 'pdf' | 'docx' | 'xlsx' | 'image';
  subject_tag: string | null;
  chapter_tag: string | null;
  status: 'uploading' | 'ocr_processing' | 'embedding' | 'ready' | 'error';
  error_message: string | null;
  file_size_kb: number | null;
  page_count: number | null;
  created_at: string;
};

export type DocumentListResponse = {
  items: DocumentItem[];
  total: number;
  total_all: number;
  limit: number;
  offset: number;
};

export type DocumentStatusResponse = {
  id: number;
  status: DocumentItem['status'];
  error_message: string | null;
  page_count: number | null;
  extract_method: string | null;
  chunk_count: number;
};

export type Citation = {
  document_id: number;
  chunk_id: number;
  file_name: string;
  page_number: number | null;
  snippet: string;
  score: number;
};

export type ChatResponse = {
  answer: string;
  conversation_id: number;
  model: string;
  citations: Citation[];
  /** True khi câu trả lời có dùng ngữ cảnh trích từ tài liệu của người dùng. */
  used_documents?: boolean;
};

/** Định dạng kích thước tệp cho giao diện, đọc từ KB do backend trả về. */
export function formatFileSize(sizeKb: number | null): string {
  if (!sizeKb) return '—';
  if (sizeKb < 1024) return `${sizeKb} KB`;
  return `${(sizeKb / 1024).toFixed(1)} MB`;
}
