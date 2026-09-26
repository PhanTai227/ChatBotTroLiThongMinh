import { useEffect, useState } from 'react';
import { KeyRound, Lock, ShieldCheck, Trash2, Unlock, UserCog, Users } from 'lucide-react';
import { apiRequest, type User } from '../lib/auth';
import { StatCard } from './DashboardCards';

type Stats = { users: number; active_users: number; conversations: number; questions: number };
type Setting = { key: string; value: string; updated_at: string };

export function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<Stats>({ users: 0, active_users: 0, conversations: 0, questions: 0 });
  const [error, setError] = useState('');
  const [maxUploadMb, setMaxUploadMb] = useState('20');

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
      const [userData, statData, settingData] = await Promise.all([
        apiRequest<User[]>('/api/admin/users'),
        apiRequest<Stats>('/api/admin/stats'),
        apiRequest<Setting[]>('/api/admin/settings'),
      ]);
      setUsers(userData);
      setStats(statData);
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

  return (
    <>
      <section><p className="text-xs font-bold uppercase tracking-[0.15em] text-indigo-500">Quản trị hệ thống</p><h1 className="mt-2 text-2xl font-extrabold text-slate-950 sm:text-3xl">Bảng quản trị</h1><p className="mt-2 text-sm text-slate-500">Quản lý người dùng, quyền truy cập và hoạt động hệ thống.</p></section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Tổng tài khoản" value={String(stats.users)} detail="Tất cả người dùng" icon={Users} tone="indigo" />
        <StatCard title="Đang hoạt động" value={String(stats.active_users)} detail="Tài khoản được mở" icon={Unlock} tone="emerald" />
        <StatCard title="Cuộc hội thoại" value={String(stats.conversations)} detail="Đã lưu trong SQLite" icon={UserCog} tone="orange" />
        <StatCard title="Câu hỏi AI" value={String(stats.questions)} detail="Tổng yêu cầu người dùng" icon={ShieldCheck} tone="indigo" />
      </section>
      {error && <p className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">{error}</p>}
      <section className="overflow-hidden rounded-2xl border border-slate-100 bg-white shadow-[0_4px_20px_rgba(15,23,42,0.035)]">
        <div className="border-b border-slate-100 p-5 sm:p-6"><h2 className="font-extrabold text-slate-900">Quản lý tài khoản</h2><p className="mt-1 text-xs text-slate-400">Khóa, đổi quyền hoặc đặt lại mật khẩu người dùng.</p></div>
        <div className="divide-y divide-slate-100">
          {users.map((user) => <article key={user.id} className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center"><div className="grid size-11 shrink-0 place-items-center rounded-xl bg-indigo-50 font-extrabold text-indigo-600">{user.full_name.slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-extrabold text-slate-800">{user.full_name}</p><span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${user.role === 'admin' ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'}`}>{user.role}</span><span className={`size-2 rounded-full ${user.is_active ? 'bg-emerald-500' : 'bg-rose-500'}`} /></div><p className="mt-1 text-xs text-slate-400">{user.email}</p></div><div className="flex flex-wrap gap-2"><select aria-label={`Vai trò ${user.email}`} value={user.role} onChange={(e) => void update(user, { role: e.target.value })} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600"><option value="user">User</option><option value="admin">Admin</option></select><button onClick={() => resetPassword(user)} className="flex items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-xs font-bold text-slate-600 hover:bg-slate-50"><KeyRound size={14} />Đặt lại MK</button><button onClick={() => void update(user, { is_active: !user.is_active })} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold ${user.is_active ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'}`}>{user.is_active ? <><Lock size={14} />Khóa</> : <><Unlock size={14} />Mở khóa</>}</button><button aria-label={`Xóa ${user.email}`} onClick={() => void deleteUser(user)} className="flex items-center gap-2 rounded-lg border border-rose-100 px-3 py-2 text-xs font-bold text-rose-600 hover:bg-rose-50"><Trash2 size={14} />Xóa</button></div></article>)}
        </div>
      </section>
      <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
        <h2 className="font-extrabold text-slate-900">Cấu hình hệ thống</h2><p className="mt-1 text-xs text-slate-400">Thiết lập giới hạn tải tài liệu cho học viên.</p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end"><label className="flex-1"><span className="mb-2 block text-xs font-bold text-slate-600">Dung lượng tối đa (MB)</span><input type="number" min="1" max="500" value={maxUploadMb} onChange={(e) => setMaxUploadMb(e.target.value)} className="h-11 w-full rounded-xl border border-slate-200 px-4 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100" /></label><button onClick={() => void saveMaxUpload()} className="h-11 rounded-xl bg-slate-900 px-5 text-xs font-extrabold text-white hover:bg-indigo-700">Lưu cấu hình</button></div>
      </section>
    </>
  );
}
