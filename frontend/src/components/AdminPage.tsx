import { useEffect, useState } from 'react';
import { History, KeyRound, Lock, MessageSquareHeart, ShieldCheck, Trash2, Unlock, UserCog, Users, X } from 'lucide-react';
import { apiRequest, type User } from '../lib/auth';
import { StatCard } from './DashboardCards';

type Stats = { users: number; active_users: number; conversations: number; questions: number; feedback_new: number };
type Setting = { key: string; value: string; updated_at: string };

type FeedbackItem = {
  id: number;
  rating: number;
  category: 'bug' | 'suggestion' | 'praise' | 'other';
  content: string;
  status: 'new' | 'read' | 'replied';
  admin_reply: string | null;
  created_at: string;
  user_id: number;
  full_name: string;
  email: string;
};

type ChatMessage = { id: number; role: 'user' | 'assistant'; content: string; created_at: string };
type UserConversation = { id: number; title: string; created_at: string; message_count: number; messages: ChatMessage[] };

const categoryLabels: Record<FeedbackItem['category'], string> = {
  bug: 'Lỗi hệ thống',
  suggestion: 'Góp ý cải thiện',
  praise: 'Đánh giá tốt',
  other: 'Khác',
};

export function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<Stats>({ users: 0, active_users: 0, conversations: 0, questions: 0, feedback_new: 0 });
  const [error, setError] = useState('');
  const [maxUploadMb, setMaxUploadMb] = useState('20');
  const [feedbacks, setFeedbacks] = useState<FeedbackItem[]>([]);
  const [replyingId, setReplyingId] = useState<number | null>(null);
  const [replyText, setReplyText] = useState('');
  const [historyUser, setHistoryUser] = useState<User | null>(null);
  const [history, setHistory] = useState<UserConversation[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const saveMaxUpload = async () => {
    try {
      await apiRequest('/api/admin/settings/max_upload_mb', { method: 'PATCH', body: JSON.stringify({ value: maxUploadMb }) });
      setError('');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Lưu cấu hình thất bại.');
    }
  };

  const load = async () => {
    try {
      const [userData, statData, settingData, feedbackData] = await Promise.all([
        apiRequest<User[]>('/api/admin/users'),
        apiRequest<Stats>('/api/admin/stats'),
        apiRequest<Setting[]>('/api/admin/settings'),
        apiRequest<{ items: FeedbackItem[] }>('/api/admin/feedback'),
      ]);
      setUsers(userData);
      setStats(statData);
      setFeedbacks(feedbackData.items);
      const uploadSetting = settingData.find((setting) => setting.key === 'max_upload_mb');
      if (uploadSetting) setMaxUploadMb(uploadSetting.value);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Không tải được dữ liệu Admin.');
    }
  };

  useEffect(() => { void load(); }, []);

  const update = async (user: User, changes: { is_active?: boolean; role?: string; new_password?: string }) => {
    setError('');
    try {
      await apiRequest('/api/admin/users', { method: 'PATCH', body: JSON.stringify({ user_id: user.id, ...changes }) });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Cập nhật thất bại.');
    }
  };

  const deleteUser = async (user: User) => {
    if (!window.confirm(`Xóa tài khoản ${user.email}? Thao tác này không thể hoàn tác.`)) return;
    try {
      await apiRequest(`/api/admin/users/${user.id}`, { method: 'DELETE' });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Xóa tài khoản thất bại.');
    }
  };

  const resetPassword = (user: User) => {
    const password = window.prompt(`Nhập mật khẩu mới cho ${user.email} (tối thiểu 8 ký tự):`);
    if (password && password.length >= 8) void update(user, { new_password: password });
  };

  const markFeedbackRead = async (id: number) => {
    setError('');
    try {
      await apiRequest(`/api/admin/feedback/${id}`, { method: 'PATCH' });
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Cập nhật phản hồi thất bại.');
    }
  };

  const sendReply = async (id: number) => {
    if (!replyText.trim()) return;
    setError('');
    try {
      await apiRequest(`/api/admin/feedback/${id}/reply`, {
        method: 'POST',
        body: JSON.stringify({ admin_reply: replyText.trim() }),
      });
      setReplyingId(null);
      setReplyText('');
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Trả lời phản hồi thất bại.');
    }
  };

  const openHistory = async (user: User) => {
    setError('');
    setHistoryUser(user);
    setHistory([]);
    setHistoryLoading(true);
    try {
      const data = await apiRequest<{ conversations: UserConversation[] }>(`/api/admin/users/${user.id}/history`);
      setHistory(data.conversations);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Không tải được lịch sử hỏi.');
    } finally {
      setHistoryLoading(false);
    }
  };

  return (
    <>
      <section>
        <p className="eyebrow text-accent">Quản trị hệ thống</p>
        <h1 className="page-title mt-2 text-3xl text-ink">Bảng quản trị</h1>
        <p className="mt-2 text-sm text-muted">Quản lý người dùng, quyền truy cập và hoạt động hệ thống.</p>
      </section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Tổng tài khoản" value={String(stats.users)} detail="Tất cả người dùng" icon={Users} tone="indigo" />
        <StatCard title="Đang hoạt động" value={String(stats.active_users)} detail="Tài khoản được mở" icon={Unlock} tone="emerald" />
        <StatCard title="Cuộc hội thoại" value={String(stats.conversations)} detail="Đã lưu trong SQLite" icon={UserCog} tone="orange" />
        <StatCard title="Phản hồi mới" value={String(stats.feedback_new)} detail="Chưa xem" icon={MessageSquareHeart} tone="indigo" />
      </section>
      {error && <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}
      <section className="card overflow-hidden">
        <div className="border-b border-line p-5 sm:p-6"><h2 className="section-title text-ink">Quản lý tài khoản</h2><p className="mt-1 text-xs text-muted">Khóa, đổi quyền hoặc đặt lại mật khẩu người dùng.</p></div>
        <div className="divide-y divide-line">
          {users.map((user) => <article key={user.id} className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center"><div className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent-soft font-bold text-accent">{user.full_name.slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-ink">{user.full_name}</p><span className={`pill ${user.role === 'admin' ? 'bg-accent-soft text-accent' : 'bg-[#efece3] text-muted'}`}>{user.role}</span><span className={`size-2 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} /></div><p className="mt-1 text-xs text-muted">{user.email}</p></div><div className="flex flex-wrap gap-2"><button onClick={() => void openHistory(user)} className="btn btn-outline px-3 py-2 text-xs"><History size={14} />Lịch sử hỏi</button><select aria-label={`Vai trò ${user.email}`} value={user.role} onChange={(e) => void update(user, { role: e.target.value })} className="input w-auto px-3 py-2 text-xs font-semibold text-muted"><option value="user">User</option><option value="admin">Admin</option></select><button onClick={() => resetPassword(user)} className="btn btn-outline px-3 py-2 text-xs"><KeyRound size={14} />Đặt lại MK</button><button onClick={() => void update(user, { is_active: !user.is_active })} className={`btn px-3 py-2 text-xs ${user.is_active ? 'bg-rose-50 text-rose-600 hover:bg-rose-100' : 'bg-accent-soft text-accent hover:bg-[#dde9e0]'}`}>{user.is_active ? <><Lock size={14} />Khóa</> : <><Unlock size={14} />Mở khóa</>}</button><button aria-label={`Xóa ${user.email}`} onClick={() => void deleteUser(user)} className="btn border border-rose-200 px-3 py-2 text-xs text-rose-600 hover:bg-rose-50"><Trash2 size={14} />Xóa</button></div></article>)}
        </div>
      </section>
      <section className="card p-5 sm:p-6">
        <h2 className="section-title text-ink">Phản hồi từ học viên</h2>
        <p className="mt-1 text-xs text-muted">Đánh giá, góp ý và báo lỗi gửi tới quản trị.</p>
        <div className="mt-4 space-y-3">
          {feedbacks.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line bg-paper py-10 text-center">
              <p className="font-semibold text-ink">Chưa có phản hồi nào</p>
            </div>
          )}
          {feedbacks.map((feedback) => (
            <article key={feedback.id} className="rounded-xl border border-line bg-paper p-4">
              <div className="flex flex-wrap items-center gap-2">
                <div className="grid size-9 shrink-0 place-items-center rounded-lg bg-accent-soft font-bold text-accent">{feedback.full_name.slice(0, 1).toUpperCase()}</div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-semibold text-ink">{feedback.full_name}</p>
                  <p className="text-[11px] text-muted">{feedback.email} · {feedback.rating}/5 sao · {categoryLabels[feedback.category]}</p>
                </div>
                <span className={`pill ${feedback.status === 'new' ? 'bg-amber-50 text-amber-700' : feedback.status === 'read' ? 'bg-sky-50 text-sky-700' : 'bg-emerald-50 text-emerald-700'}`}>
                  {feedback.status === 'new' ? 'Chờ xem' : feedback.status === 'read' ? 'Đã xem' : 'Đã trả lời'}
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-ink">{feedback.content}</p>
              {feedback.admin_reply && (
                <p className="mt-2 rounded-lg border-l-4 border-accent bg-accent-soft px-3 py-2 text-sm leading-6 text-ink"><span className="text-[10px] font-bold uppercase tracking-wider text-accent">Đã trả lời: </span>{feedback.admin_reply}</p>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {feedback.status === 'new' && (
                  <button onClick={() => void markFeedbackRead(feedback.id)} className="btn btn-outline px-3 py-2 text-xs">Đánh dấu đã xem</button>
                )}
                {replyingId === feedback.id ? (
                  <>
                    <input value={replyText} onChange={(e) => setReplyText(e.target.value)} placeholder="Nhập câu trả lời..." maxLength={2000} className="input min-w-[220px] flex-1 py-2 text-xs" />
                    <button onClick={() => void sendReply(feedback.id)} disabled={!replyText.trim()} className="btn btn-primary px-3 py-2 text-xs disabled:cursor-not-allowed disabled:bg-line">Gửi</button>
                    <button onClick={() => { setReplyingId(null); setReplyText(''); }} className="btn btn-outline px-3 py-2 text-xs">Hủy</button>
                  </>
                ) : (
                  <button onClick={() => { setReplyingId(feedback.id); setReplyText(feedback.admin_reply ?? ''); }} className="btn btn-outline px-3 py-2 text-xs">Trả lời</button>
                )}
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="card p-5 sm:p-6">
        <h2 className="section-title text-ink">Cấu hình hệ thống</h2>
        <p className="mt-1 text-xs text-muted">Thiết lập giới hạn tải tài liệu cho học viên.</p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex-1"><span className="field-label">Dung lượng tối đa (MB)</span><input type="number" min="1" max="500" value={maxUploadMb} onChange={(e) => setMaxUploadMb(e.target.value)} className="input" /></label>
          <button onClick={() => void saveMaxUpload()} className="btn btn-primary px-5 py-3 text-xs">Lưu cấu hình</button>
        </div>
      </section>
      {historyUser && (
        <div className="fixed inset-0 z-[70] grid place-items-center bg-ink/45 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) setHistoryUser(null); }}>
          <div role="dialog" aria-modal="true" className="flex max-h-[85vh] w-full max-w-2xl flex-col rounded-2xl bg-surface p-6 shadow-2xl">
            <div className="flex items-start justify-between">
              <div><span className="eyebrow text-accent">Lịch sử hỏi đáp</span><h2 className="section-title mt-1 text-xl text-ink">{historyUser.full_name}</h2><p className="mt-1 text-xs text-muted">{historyUser.email}</p></div>
              <button aria-label="Đóng" onClick={() => setHistoryUser(null)} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink"><X size={19} /></button>
            </div>
            <div className="mt-4 min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
              {historyLoading && <p className="py-8 text-center text-sm text-muted">Đang tải...</p>}
              {!historyLoading && history.length === 0 && <p className="py-8 text-center text-sm text-muted">Người dùng chưa hỏi câu nào.</p>}
              {history.map((conversation) => (
                <div key={conversation.id} className="rounded-xl border border-line bg-paper p-4">
                  <p className="text-sm font-semibold text-ink">{conversation.title}</p>
                  <div className="mt-3 space-y-2">
                    {conversation.messages.map((message) => (
                      <div key={message.id} className={`max-w-[92%] rounded-xl px-3.5 py-2.5 text-sm leading-6 ${message.role === 'user' ? 'ml-auto bg-accent text-white' : 'border border-line bg-surface text-ink'}`}>
                        <p className="whitespace-pre-line">{message.content}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
