import { useState } from 'react';
import { BookOpen, CheckCircle2, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck, UserRound } from 'lucide-react';
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
    <main className="grid min-h-screen bg-paper lg:grid-cols-[1.05fr_0.95fr]">
      <section className="hidden flex-col justify-between bg-ink p-12 text-paper lg:flex">
        <div className="flex items-center gap-3">
          <div className="grid size-10 place-items-center rounded-lg bg-accent text-white"><BookOpen size={20} /></div>
          <div>
            <p className="section-title text-lg text-paper">Mindora</p>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-white/40">Học tập thông minh</p>
          </div>
        </div>
        <div className="max-w-lg">
          <h1 className="page-title text-4xl leading-tight text-paper">Học thông minh với tài liệu của riêng bạn.</h1>
          <p className="mt-5 text-sm leading-7 text-white/60">Trợ lý ảo thông minh hoạt động hoàn toàn trên máy, bảo vệ tài liệu và quản lý tiến độ học tập của bạn.</p>
          <div className="mt-8 grid gap-3 text-sm text-white/70">
            <p className="flex items-center gap-3"><CheckCircle2 size={17} className="shrink-0 text-accent-soft" />AI local Qwen 2.5 3B, không tốn phí API</p>
            <p className="flex items-center gap-3"><CheckCircle2 size={17} className="shrink-0 text-accent-soft" />Dữ liệu và tài khoản lưu bằng SQLite</p>
            <p className="flex items-center gap-3"><CheckCircle2 size={17} className="shrink-0 text-accent-soft" />Phân quyền người dùng và quản trị viên</p>
          </div>
        </div>
        <p className="text-xs text-white/30">Mindora Local Learning Assistant</p>
      </section>
      <section className="flex items-center justify-center px-5 py-10 sm:px-10">
        <div className="w-full max-w-md card p-7 sm:p-9">
          <div className="mb-7 flex items-center gap-2.5 lg:hidden">
            <div className="grid size-9 place-items-center rounded-lg bg-accent text-white"><BookOpen size={18} /></div>
            <p className="section-title text-lg text-ink">Mindora</p>
          </div>
          <p className="eyebrow text-accent">{mode === 'login' ? 'Chào mừng trở lại' : 'Tạo tài khoản mới'}</p>
          <h2 className="page-title mt-2 text-2xl text-ink">{mode === 'login' ? 'Đăng nhập Mindora' : 'Bắt đầu học tập'}</h2>
          <p className="mt-2 text-sm text-muted">{mode === 'login' ? 'Nhập thông tin để tiếp tục phiên học tập.' : 'Tạo tài khoản học viên hoàn toàn miễn phí.'}</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            {mode === 'register' && (
              <label className="block">
                <span className="field-label">Họ và tên</span>
                <div className="relative">
                  <UserRound className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" size={17} />
                  <input required value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Nguyễn Văn A" className="input input-icon" />
                </div>
              </label>
            )}
            <label className="block">
              <span className="field-label">Email</span>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" size={17} />
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="email@example.com" className="input input-icon" />
              </div>
            </label>
            <label className="block">
              <span className="field-label">Mật khẩu</span>
              <div className="relative">
                <LockKeyhole className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" size={17} />
                <input type={showPassword ? 'text' : 'password'} required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Tối thiểu 8 ký tự" className="input input-icon input-action" />
                <button type="button" aria-label="Hiện mật khẩu" onClick={() => setShowPassword((value) => !value)} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-muted hover:bg-[#efece3] hover:text-ink">{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button>
              </div>
            </label>
            {error && <p className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-xs font-semibold text-rose-700">{error}</p>}
            <button disabled={loading} className="btn btn-primary w-full">{loading ? 'Đang xử lý...' : mode === 'login' ? 'Đăng nhập' : 'Tạo tài khoản'} <ShieldCheck size={17} /></button>
          </form>

          <div className="mt-6 rounded-lg bg-amber-50 p-3 text-[11px] leading-5 text-amber-800">Tài khoản Admin demo:<br /><b>admin@mindora.local</b> / <b>Admin@123</b></div>
          <p className="mt-6 text-center text-sm text-muted">{mode === 'login' ? 'Chưa có tài khoản?' : 'Đã có tài khoản?'} <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); }} className="font-semibold text-accent hover:text-accent-deep">{mode === 'login' ? 'Đăng ký' : 'Đăng nhập'}</button></p>
        </div>
      </section>
    </main>
  );
}

