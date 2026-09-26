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

  const response = await fetch(`http://127.0.0.1:8000${path}`, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || 'Không thể kết nối máy chủ.');
  return data as T;
}
