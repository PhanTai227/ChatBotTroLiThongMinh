import { useEffect, useState } from 'react';
import { StatCard } from './components/DashboardCards';
import { DailyGoal, WeeklyChart } from './components/LearningPanels';
import { DocumentsPage } from './components/DocumentsPage';
import { AiChatPage } from './components/AiChatPage';
import { QuizPage } from './components/QuizPage';
import { HistoryPage } from './components/HistoryPage';
import { ProgressPage } from './components/ProgressPage';
import { AuthPage } from './components/AuthPage';
import { AdminPage } from './components/AdminPage';
import { apiRequest, clearToken, getToken, type AuthResponse, type User } from './lib/auth';
import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  BookOpen,
  Bot,
  ChevronRight,
  Clock3,
  FileText,
  Home,
  Library,
  LogOut,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react';

const navItems: { label: string; icon: LucideIcon }[] = [
  { label: 'Tổng quan', icon: Home },
  { label: 'Tài liệu', icon: Library },
  { label: 'Trợ lý AI', icon: Bot },
  { label: 'Bài tập & Quiz', icon: FileText },
  { label: 'Lịch sử học tập', icon: Clock3 },
  { label: 'Tiến độ học tập', icon: BarChart3 },
];

const quickActions = [
  { title: 'Tải tài liệu lên', description: 'PDF, Word, Excel hoặc ảnh', icon: Upload },
  { title: 'Hỏi trợ lý AI', description: 'Giải thích và hỗ trợ bài học', icon: MessageSquareText },
  { title: 'Tạo bài ôn tập', description: 'Sinh quiz từ tài liệu của bạn', icon: Sparkles },
];

const documents = [
  { title: 'Giáo trình Trí tuệ nhân tạo', type: 'PDF', pages: '42 trang', time: '10 phút trước', color: 'bg-rose-50 text-rose-600' },
  { title: 'Slide Thuật toán tối ưu', type: 'PDF', pages: '28 trang', time: 'Hôm qua', color: 'bg-amber-50 text-amber-600' },
  { title: 'Bài tập Giải thuật tuần 3', type: 'DOCX', pages: '12 trang', time: '2 ngày trước', color: 'bg-sky-50 text-sky-600' },
];

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

function QuickAction({ item }: { item: (typeof quickActions)[number] }) {
  return (
    <button className="card group flex items-center gap-4 p-4 text-left transition hover:border-accent">
      <div className="grid size-10 shrink-0 place-items-center rounded-lg bg-accent-soft text-accent transition group-hover:bg-accent group-hover:text-white"><item.icon size={19} /></div>
      <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-ink">{item.title}</p><p className="mt-0.5 truncate text-xs text-muted">{item.description}</p></div>
      <ChevronRight className="text-muted transition group-hover:translate-x-0.5 group-hover:text-accent" size={17} />
    </button>
  );
}

function RecentDocuments() {
  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-4"><h2 className="section-title text-ink">Tài liệu gần đây</h2><p className="mt-1 text-xs text-muted">Tiếp tục học từ tài liệu đã tải lên</p></div>
      <div className="divide-y divide-line">
        {documents.map((doc) => (
          <button key={doc.title} className="group flex w-full items-center gap-3 py-3 text-left first:pt-0 last:pb-0">
            <div className={`grid size-10 shrink-0 place-items-center rounded-lg text-[10px] font-bold ${doc.color}`}>{doc.type}</div>
            <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink group-hover:text-accent">{doc.title}</p><p className="mt-0.5 text-[11px] text-muted">{doc.pages} · {doc.time}</p></div>
            <MoreHorizontal size={17} className="text-line" />
          </button>
        ))}
      </div>
    </section>
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
        ) : activePage === 'Bài tập & Quiz' ? (
          <QuizPage />
        ) : activePage === 'Lịch sử học tập' ? (
          <HistoryPage />
        ) : activePage === 'Tiến độ học tập' ? (
          <ProgressPage />
        ) : activePage === 'Tài liệu' ? (
          <DocumentsPage />
        ) : (
            <>
          <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <p className="eyebrow text-accent">Không gian cá nhân</p>
              <h1 className="page-title mt-2 text-3xl text-ink">Chào buổi sáng, An!</h1>
              <p className="mt-2 text-sm text-muted">Bạn đang có một ngày học tập hiệu quả. Tiếp tục thôi!</p>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard title="Tài liệu đã học" value="24" detail="↗ 3 tài liệu trong tuần này" icon={BookOpen} tone="indigo" />
            <StatCard title="Câu hỏi đã hỏi" value="186" detail="↗ 12% so với tuần trước" icon={MessageSquareText} tone="orange" />
            <StatCard title="Bài đã hoàn thành" value="32" detail="↗ 8 bài trong tuần này" icon={FileText} tone="emerald" />
          </section>

          <section>
            <div className="mb-4"><h2 className="section-title text-ink">Bắt đầu nhanh</h2><p className="mt-1 text-xs text-muted">Tính năng bạn có thể sử dụng ngay</p></div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{quickActions.map((item) => <QuickAction key={item.title} item={item} />)}</div>
          </section>

          <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.65fr_1fr]">
            <div className="card p-5 sm:p-6">
              <div className="mb-2"><h2 className="section-title text-ink">Hoạt động học tập</h2><p className="mt-1 text-xs text-muted">Thời gian học trong 7 ngày qua</p></div>
              <WeeklyChart />
            </div>
            <DailyGoal />
          </section>

          <RecentDocuments />
            </>
          )}
        </main>
      </div>
    </div>
  );
}


