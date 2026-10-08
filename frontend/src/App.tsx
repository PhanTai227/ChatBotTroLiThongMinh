import { useEffect, useState } from 'react';
import { StatCard } from './components/DashboardCards';
import { DocumentsPage } from './components/DocumentsPage';
import { AiChatPage } from './components/AiChatPage';
import { FeedbackPage } from './components/FeedbackPage';
import { AuthPage } from './components/AuthPage';
import { AdminPage } from './components/AdminPage';
import { apiRequest, clearToken, getToken, type AuthResponse, type User } from './lib/auth';
import type { LucideIcon } from 'lucide-react';
import {
  BookOpen,
  Bot,
  ChevronRight,
  Home,
  Library,
  LogOut,
  Menu,
  MessageSquareText,
  MessageSquareHeart,
  ShieldCheck,
  Upload,
  X,
} from 'lucide-react';

const navItems: { label: string; icon: LucideIcon }[] = [
  { label: 'Tổng quan', icon: Home },
  { label: 'Tài liệu', icon: Library },
  { label: 'Trợ lý AI', icon: Bot },
  { label: 'Phản hồi', icon: MessageSquareHeart },
];

const quickActions = [
  { title: 'Tải tài liệu lên', description: 'PDF, Word, Excel hoặc ảnh', icon: Upload, page: 'Tài liệu' },
  { title: 'Hỏi trợ lý AI', description: 'Giải thích và hỗ trợ bài học', icon: MessageSquareText, page: 'Trợ lý AI' },
  { title: 'Gửi phản hồi', description: 'Đánh giá và góp ý cho quản trị', icon: MessageSquareHeart, page: 'Phản hồi' },
];

type ProgressOverview = { documents: number; questions: number; conversations: number };
type ProgressActivity = {
  id: string;
  type: string;
  title: string;
  detail: string;
  subject: string | null;
  at: string;
};

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-1">
      <div className="grid size-9 place-items-center rounded-lg bg-accent text-white">
        <BookOpen size={18} strokeWidth={2.2} />
      </div>
      <div>
        <p className="section-title text-[17px] text-ink">Mindora</p>
        <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Học tập thông minh</p>
      </div>
    </div>
  );
}

function Sidebar({ open, onClose, activePage, onNavigate, role }: { open: boolean; onClose: () => void; activePage: string; onNavigate: (page: string) => void; role: 'user' | 'admin' }) {
  const visibleItems = role === 'admin' ? [...navItems, { label: 'Quản trị', icon: ShieldCheck }] : navItems;
  return (
    <>
      {open && <button aria-label="Đóng menu" className="fixed inset-0 z-40 bg-ink/40 lg:hidden" onClick={onClose} />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[248px] flex-col border-r border-line bg-surface px-4 py-6 transition-transform duration-300 lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-8 flex items-center justify-between">
          <Brand />
          <button aria-label="Đóng menu" className="rounded-lg p-2 text-muted hover:bg-[#efece3] hover:text-ink lg:hidden" onClick={onClose}><X size={18} /></button>
        </div>

        <p className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.16em] text-muted">Không gian học tập</p>
        <nav className="space-y-1">
          {visibleItems.map((item) => (
            <button key={item.label} onClick={() => onNavigate(item.label)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition ${activePage === item.label ? 'bg-accent-soft text-accent' : 'text-muted hover:bg-[#efece3] hover:text-ink'}`}>
              <item.icon size={18} />
              <span className="flex-1 text-left">{item.label}</span>
            </button>
          ))}
        </nav>
      </aside>
    </>
  );
}

function Header({ onMenu, user, onLogout }: { onMenu: () => void; user: User; onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-paper/90 backdrop-blur">
      <div className="flex h-16 items-center gap-4 px-4 sm:px-7 lg:px-9">
        <button aria-label="Mở menu" onClick={onMenu} className="rounded-lg border border-line bg-surface p-2.5 text-muted hover:text-ink lg:hidden"><Menu size={19} /></button>
        <div className="ml-auto flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-lg bg-accent text-xs font-bold text-white">{user.full_name.slice(0, 1).toUpperCase()}</div>
          <div className="hidden sm:block"><p className="text-sm font-semibold text-ink">{user.full_name}</p><p className="text-[11px] text-muted">{user.role === 'admin' ? 'Quản trị viên' : 'Học viên'}</p></div>
          <button aria-label="Đăng xuất" onClick={onLogout} className="rounded-lg p-2.5 text-muted transition hover:bg-rose-50 hover:text-rose-600"><LogOut size={17} /></button>
        </div>
      </div>
    </header>
  );
}

function QuickAction({ item, onGo }: { item: (typeof quickActions)[number]; onGo: (page: string) => void }) {
  return (
    <button onClick={() => onGo(item.page)} className="card group flex items-center gap-4 p-4 text-left transition hover:border-accent">
      <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent transition group-hover:bg-accent group-hover:text-white"><item.icon size={19} /></div>
      <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-ink">{item.title}</p><p className="mt-0.5 truncate text-xs text-muted">{item.description}</p></div>
      <ChevronRight className="text-muted transition group-hover:translate-x-0.5 group-hover:text-accent" size={17} />
    </button>
  );
}

/** Trang Tổng quan dùng số liệu thật từ /api/progress thay vì dữ liệu giả. */
function OverviewPage({ onGo }: { onGo: (page: string) => void }) {
  const [overview, setOverview] = useState<ProgressOverview | null>(null);
  const [activities, setActivities] = useState<ProgressActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<{ overview: ProgressOverview; activities: ProgressActivity[] }>('/api/progress')
      .then((data) => {
        setOverview(data.overview);
        setActivities(data.activities.slice(0, 5));
      })
      .catch(() => undefined)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow text-accent">Không gian cá nhân</p>
          <h1 className="page-title mt-2 text-3xl text-ink">Tổng quan học tập</h1>
          <p className="mt-2 text-sm text-muted">Số liệu cập nhật theo hoạt động thật của bạn.</p>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tài liệu" value={loading ? '…' : String(overview?.documents ?? 0)} detail="Đã tải lên hệ thống" icon={BookOpen} tone="indigo" />
        <StatCard title="Câu hỏi đã hỏi" value={loading ? '…' : String(overview?.questions ?? 0)} detail="Đã hỏi trợ lý AI" icon={MessageSquareText} tone="orange" />
        <StatCard title="Hội thoại" value={loading ? '…' : String(overview?.conversations ?? 0)} detail="Cuộc trò chuyện với AI" icon={Bot} tone="emerald" />
      </section>

      <section>
        <div className="mb-4"><h2 className="section-title text-ink">Bắt đầu nhanh</h2><p className="mt-1 text-xs text-muted">Tính năng bạn có thể sử dụng ngay</p></div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{quickActions.map((item) => <QuickAction key={item.title} item={item} onGo={onGo} />)}</div>
      </section>

      <section className="card p-5 sm:p-6">
        <div className="mb-4"><h2 className="section-title text-ink">Hoạt động gần đây</h2><p className="mt-1 text-xs text-muted">Hỏi đáp và tài liệu mới nhất của bạn</p></div>
        {loading && <p className="py-6 text-center text-sm text-muted">Đang tải...</p>}
        {!loading && activities.length === 0 && (
          <div className="rounded-2xl border border-dashed border-line bg-paper py-10 text-center">
            <p className="font-semibold text-ink">Chưa có hoạt động nào</p>
            <p className="mt-1 text-sm text-muted">Hãy tải tài liệu lên rồi đặt câu hỏi đầu tiên.</p>
          </div>
        )}
        <div className="divide-y divide-line">
          {activities.map((activity) => (
            <div key={activity.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
              <div className={`grid size-10 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${activity.type === 'Chat AI' ? 'bg-accent-soft text-accent' : 'bg-sky-50 text-sky-700'}`}>
                {activity.type === 'Chat AI' ? 'AI' : 'TL'}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink">{activity.title}</p>
                <p className="mt-0.5 truncate text-[11px] text-muted">{activity.detail}{activity.subject ? ` · ${activity.subject}` : ''}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

export default function App() {
  const [auth, setAuth] = useState<AuthResponse | null>(null);
  const [checkingSession, setCheckingSession] = useState(Boolean(getToken()));
  const [menuOpen, setMenuOpen] = useState(false);
  const [activePage, setActivePage] = useState('Tổng quan');

  useEffect(() => {
    if (!getToken()) return;
    apiRequest<{ user: User }>('/api/auth/me')
      .then((data) => setAuth({ token: getToken() || '', user: data.user }))
      .catch(() => clearToken())
      .finally(() => setCheckingSession(false));
  }, []);

  if (checkingSession) return <div className="grid min-h-screen place-items-center bg-paper text-sm font-semibold text-muted">Đang kiểm tra phiên đăng nhập...</div>;
  if (!auth) return <AuthPage onAuthenticated={setAuth} />;

  const logout = async () => {
    try { await apiRequest('/api/auth/logout', { method: 'POST' }); } catch { /* phiên có thể đã hết hạn */ }
    clearToken();
    setAuth(null);
    setActivePage('Tổng quan');
  };

  const navigate = (page: string) => {
    if (page === 'Quản trị' && auth.user.role !== 'admin') return;
    setActivePage(page);
    setMenuOpen(false);
  };

  return (
    <div className="min-h-screen">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} activePage={activePage} onNavigate={navigate} role={auth.user.role} />
      <div className="min-h-screen lg:pl-[248px]">
        <Header onMenu={() => setMenuOpen(true)} user={auth.user} onLogout={() => void logout()} />
        <main className="mx-auto max-w-[1500px] space-y-7 p-4 sm:p-7 lg:p-9">
        {activePage === 'Quản trị' && auth.user.role === 'admin' ? (
          <AdminPage />
        ) : activePage === 'Trợ lý AI' ? (
          <AiChatPage />
        ) : activePage === 'Phản hồi' ? (
          <FeedbackPage />
        ) : activePage === 'Tài liệu' ? (
          <DocumentsPage />
        ) : (
          <OverviewPage onGo={navigate} />
        )}
        </main>
      </div>
    </div>
  );
}


