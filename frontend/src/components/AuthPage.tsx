import { useState } from 'react';
import { BookOpen, CheckCircle2, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, Sparkles, UserRound } from 'lucide-react';
import { apiRequest, setToken, type AuthResponse } from '../lib/auth';

export function AuthPage({ onAuthenticated }: { onAuthenticated: (auth: AuthResponse) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const path = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const body = mode === 'login' ? { email, password } : { full_name: fullName, email, password };
      const data = await apiRequest<AuthResponse>(path, { method: 'POST', body: JSON.stringify(body) });
      setToken(data.token);
      onAuthenticated(data);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Đăng nhập thất bại.');
    } finally {
      setLoading(false);
    }
  };
  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_0.95fr]">
      <section className="relative hidden overflow-hidden bg-[#111827] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -left-20 top-20 size-80 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="absolute -bottom-24 right-0 size-96 rounded-full bg-violet-500/20 blur-3xl" />
        <div className="relative flex items-center gap-3"><div className="grid size-11 place-items-center rounded-2xl bg-indigo-500"><BookOpen size={23} /></div><div><p className="text-lg font-extrabold">Mindora</p><p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Học tập thông minh</p></div></div>
        <div className="relative max-w-lg"><div className="mb-5 grid size-14 place-items-center rounded-2xl bg-white/10 text-indigo-300"><Sparkles size={28} /></div><h1 className="text-4xl font-extrabold leading-tight">Học thông minh với tài liệu của riêng bạn.</h1><p className="mt-5 text-sm leading-7 text-slate-400">Trợ lý ảo thông minh hoạt động hoàn toàn trên máy, bảo vệ tài liệu và quản lý tiến độ học tập của bạn.</p><div className="mt-8 grid gap-3 text-sm text-slate-300"><p className="flex items-center gap-3"><CheckCircle2 size={18} className="text-emerald-400" />AI local Qwen 2.5 3B, không tốn phí API</p><p className="flex items-center gap-3"><CheckCircle2 size={18} className="text-emerald-400" />Dữ liệu và tài khoản lưu bằng SQLite</p><p className="flex items-center gap-3"><CheckCircle2 size={18} className="text-emerald-400" />Phân quyền người dùng và quản trị viên</p></div></div>
        <p className="relative text-xs text-slate-600">Mindora Local Learning Assistant</p>
      </section>
      <section className="flex items-center justify-center bg-[#f8f9fc] px-5 py-10 sm:px-10">
        <div className="w-full max-w-md rounded-3xl border border-slate-100 bg-white p-7 shadow-xl shadow-slate-200/50 sm:p-9">
          <div className="mb-7 flex items-center gap-3 lg:hidden"><div className="grid size-10 place-items-center rounded-2xl bg-indigo-600 text-white"><BookOpen size={21} /></div><p className="text-lg font-extrabold text-slate-900">Mindora</p></div>
          <p className="text-xs font-extrabold uppercase tracking-[0.15em] text-indigo-600">{mode === 'login' ? 'Chào mừng trở lại' : 'Tạo tài khoản mới'}</p>
          <h2 className="mt-2 text-2xl font-extrabold text-slate-950">{mode === 'login' ? 'Đăng nhập Mindora' : 'Bắt đầu học tập'}</h2>
          <p className="mt-2 text-sm text-slate-400">{mode === 'login' ? 'Nhập thông tin để tiếp tục phiên học tập.' : 'Tạo tài khoản học viên hoàn toàn miễn phí.'}</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            {mode === 'register' && <label className="block"><span className="mb-2 block text-xs font-bold text-slate-600">Họ và tên</span><div className="relative"><UserRound className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} /><input required value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Nguyễn Văn A" className="h-12 w-full rounded-xl border border-slate-200 pl-11 pr-4 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100" /></div></label>}
            <label className="block"><span className="mb-2 block text-xs font-bold text-slate-600">Email</span><div className="relative"><Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} /><input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@example.com" className="h-12 w-full rounded-xl border border-slate-200 pl-11 pr-4 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100" /></div></label>
            <label className="block"><span className="mb-2 block text-xs font-bold text-slate-600">Mật khẩu</span><div className="relative"><LockKeyhole className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} /><input type={showPassword ? 'text' : 'password'} required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Tối thiểu 8 ký tự" className="h-12 w-full rounded-xl border border-slate-200 pl-11 pr-12 text-sm outline-none focus:border-indigo-400 focus:ring-4 focus:ring-indigo-100" /><button type="button" aria-label="Hiện mật khẩu" onClick={() => setShowPassword((value) => !value)} className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-2 text-slate-400 hover:bg-slate-100">{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div></label>
            {error && <p className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">{error}</p>}
            <button disabled={loading} className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 text-sm font-extrabold text-white shadow-lg shadow-indigo-200 transition hover:bg-indigo-700 disabled:opacity-60">{loading ? 'Đang xử lý...' : mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'} <ShieldCheck size={18} /></button>
          </form>

          <div className="mt-6 rounded-xl bg-amber-50 p-3 text-[11px] leading-5 text-amber-800">Tài khoản Admin demo:<br /><b>admin@mindora.local</b> / <b>Admin@123</b></div>
          <p className="mt-6 text-center text-sm text-slate-500">{mode === 'login' ? 'Chưa có tài khoản?' : 'Đã có tài khoản?'} <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }} className="font-extrabold text-indigo-600 hover:text-indigo-800">{mode === 'login' ? 'Đăng ký' : 'Đăng nhập'}</button></p>
        </div>
      </section>
    </main>
  );
}

