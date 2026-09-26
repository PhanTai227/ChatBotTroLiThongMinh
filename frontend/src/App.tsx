import { useEffect, useState } from 'react';
import { ProgressRing, StatCard } from './components/DashboardCards';
import { DailyGoal, WeeklyChart } from './components/LearningPanels';
import { DocumentsPage } from './components/DocumentsPage';
import { AiChatPage } from './components/AiChatPage';
import { QuizPage } from './components/QuizPage';
import { HistoryPage } from './components/HistoryPage';
import { ProgressPage } from './components/ProgressPage';
import { AuthPage } from './components/AuthPage';
import { AdminPage } from './components/AdminPage';
import { apiRequest, clearToken, getToken, type AuthResponse, type User } from './lib/auth';
import {
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  Flame,
  Home,
  Library,
  Menu,
  MessageSquareText,
  MoreHorizontal,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  LogOut,
  Target,
  Trophy,
  Upload,
  X,
} from 'lucide-react';

const navItems = [
  { label: 'Tổng quan', icon: Home, active: true },
  { label: 'Tài liệu', icon: Library },
  { label: 'Trợ lý AI', icon: Bot, badge: 'AI' },
  { label: 'Bài tập & Quiz', icon: FileText },
  { label: 'Lịch sử học tập', icon: Clock3 },
  { label: 'Tiến độ học tập', icon: BarChart3 },
];

const quickActions = [
  { title: 'Tải tài liệu lên', description: 'PDF, Word, Excel hoặc ảnh', icon: Upload, tone: 'indigo' },
  { title: 'Hỏi trợ lý AI', description: 'Giải thích và hỗ trợ bài học', icon: MessageSquareText, tone: 'violet' },
  { title: 'Tạo bài ôn tập', description: 'Sinh quiz từ tài liệu của bạn', icon: Sparkles, tone: 'amber' },
];

const documents = [
  { title: 'Giáo trình Trí tuệ nhân tạo', type: 'PDF', pages: '42 trang', time: '10 phút trước', color: 'bg-rose-50 text-rose-600' },
  { title: 'Slide Thuật toán tối ưu', type: 'PDF', pages: '28 trang', time: 'Hôm qua', color: 'bg-amber-50 text-amber-600' },
  { title: 'Bài tập Giải thuật tuần 3', type: 'DOCX', pages: '12 trang', time: '2 ngày trước', color: 'bg-sky-50 text-sky-600' },
];

function Brand() {
  return (
    <div className="flex items-center gap-3 px-2">
      <div className="grid size-10 place-items-center rounded-2xl bg-indigo-500 text-white shadow-lg shadow-indigo-950/30">
        <BookOpen size={21} strokeWidth={2.3} />
      </div>
      <div>
        <p className="text-[17px] font-extrabold tracking-tight text-white">Mindora</p>
        <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Học tập thông minh</p>
      </div>
    </div>
  );
}

function Sidebar({ open, onClose, activePage, onNavigate, role }: { open: boolean; onClose: () => void; activePage: string; onNavigate: (page: string) => void; role: 'user' | 'admin' }) {
  const visibleItems = role === 'admin' ? [...navItems, { label: 'Quản trị', icon: ShieldCheck, badge: 'Admin' }] : navItems;
  return (
    <>
      {open && <button aria-label="Đóng menu" className="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm lg:hidden" onClick={onClose} />}
      <aside className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col bg-[#111827] px-4 py-6 transition-transform duration-300 lg:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-8 flex items-center justify-between">
          <Brand />
          <button aria-label="Đóng menu" className="rounded-lg p-2 text-slate-400 hover:bg-white/10 hover:text-white lg:hidden" onClick={onClose}><X size={20} /></button>
        </div>

        <p className="mb-3 px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">Không gian học tập</p>
        <nav className="space-y-1">
          {visibleItems.map((item) => (
            <button key={item.label} onClick={() => onNavigate(item.label)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition ${activePage === item.label ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-950/20' : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'}`}>
              <item.icon size={19} />
              <span className="flex-1">{item.label}</span>
              {item.badge && <span className={`rounded-md px-1.5 py-0.5 text-[9px] font-extrabold ${activePage === item.label ? 'bg-white/20' : 'bg-violet-500/15 text-violet-300'}`}>{item.badge}</span>}
            </button>
          ))}
        </nav>

        <div className="mt-auto">
          <div className="mb-3 rounded-2xl border border-white/5 bg-white/[0.035] p-4">
            <div className="mb-3 flex items-center gap-2 text-indigo-300"><Trophy size={17} /><span className="text-xs font-bold">Thành tích tuần này</span></div>
            <p className="text-2xl font-extrabold text-white">1.250 <span className="text-xs font-medium text-slate-500">XP</span></p>
            <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/10"><div className="h-full w-[72%] rounded-full bg-indigo-400" /></div>
            <p className="mt-2 text-[10px] text-slate-500">Còn 480 XP để lên hạng Vàng</p>
          </div>
          <a href="#" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-slate-500 hover:bg-white/5 hover:text-white"><CircleHelp size={19} />Trợ giúp</a>
          <a href="#" className="flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-slate-500 hover:bg-white/5 hover:text-white"><Settings size={19} />Cài đặt</a>
        </div>
      </aside>
    </>
  );
}

function Header({ onMenu, user, onLogout }: { onMenu: () => void; user: User; onLogout: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-100 bg-[#f6f7fb]/90 backdrop-blur-xl">
      <div className="flex h-20 items-center gap-4 px-4 sm:px-7 lg:px-9">
        <button aria-label="Mở menu" onClick={onMenu} className="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-600 shadow-sm lg:hidden"><Menu size={20} /></button>
        <div className="relative hidden max-w-lg flex-1 sm:block">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
          <input aria-label="Tìm kiếm" className="w-full rounded-2xl border border-transparent bg-white py-3 pl-11 pr-4 text-sm shadow-[0_3px_16px_rgba(15,23,42,0.035)] outline-none transition placeholder:text-slate-400 focus:border-indigo-200 focus:ring-4 focus:ring-indigo-100" placeholder="Tìm tài liệu, câu hỏi hoặc chủ đề..." />
        </div>
        <button aria-label="Thông báo" className="relative ml-auto rounded-xl border border-slate-100 bg-white p-2.5 text-slate-500 shadow-sm transition hover:text-indigo-600"><Bell size={19} /><span className="absolute right-2 top-2 size-1.5 rounded-full bg-rose-500 ring-2 ring-white" /></button>
        <div className="flex items-center gap-3">
          <div className="grid size-9 place-items-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 text-xs font-extrabold text-white">{user.full_name.slice(0, 1).toUpperCase()}</div>
          <div className="hidden sm:block"><p className="text-sm font-bold text-slate-800">{user.full_name}</p><p className="text-[11px] font-medium text-slate-400">{user.role === 'admin' ? 'Quản trị viên' : 'Học viên'}</p></div>
          <button aria-label="Đăng xuất" onClick={onLogout} className="ml-2 rounded-xl border border-slate-200 p-2.5 text-slate-400 hover:border-rose-200 hover:bg-rose-50 hover:text-rose-600"><LogOut size={17} /></button>
        </div>
      </div>
    </header>
  );
}

function QuickAction({ item }: { item: (typeof quickActions)[number] }) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white',
    violet: 'bg-violet-50 text-violet-600 group-hover:bg-violet-600 group-hover:text-white',
    amber: 'bg-amber-50 text-amber-600 group-hover:bg-amber-500 group-hover:text-white',
  };
  return (
    <button className="group flex items-center gap-4 rounded-2xl border border-slate-100 bg-white p-4 text-left shadow-[0_4px_20px_rgba(15,23,42,0.035)] transition hover:-translate-y-1 hover:border-indigo-100 hover:shadow-lg">
      <div className={`grid size-12 shrink-0 place-items-center rounded-2xl transition ${tones[item.tone as keyof typeof tones]}`}><item.icon size={22} /></div>
      <div className="min-w-0 flex-1"><p className="text-sm font-extrabold text-slate-800">{item.title}</p><p className="mt-1 truncate text-xs text-slate-400">{item.description}</p></div>
      <ChevronRight className="text-slate-300 transition group-hover:translate-x-1 group-hover:text-indigo-500" size={18} />
    </button>
  );
}

function RecentDocuments() {
  return (
    <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
      <div className="mb-5 flex items-center justify-between"><div><h2 className="font-extrabold text-slate-900">Tài liệu gần đây</h2><p className="mt-1 text-xs text-slate-400">Tiếp tục học từ tài liệu đã tải lên</p></div><a href="#" className="text-xs font-bold text-indigo-600">Xem tất cả</a></div>
      <div className="divide-y divide-slate-100">
        {documents.map((doc) => (
          <button key={doc.title} className="group flex w-full items-center gap-3 py-3 text-left first:pt-0 last:pb-0">
            <div className={`grid size-10 shrink-0 place-items-center rounded-xl text-[10px] font-extrabold ${doc.color}`}>{doc.type}</div>
            <div className="min-w-0 flex-1"><p className="truncate text-sm font-bold text-slate-700 group-hover:text-indigo-600">{doc.title}</p><p className="mt-1 text-[11px] text-slate-400">{doc.pages} · {doc.time}</p></div>
            <MoreHorizontal size={18} className="text-slate-300" />
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

  if (checkingSession) return <div className="grid min-h-screen place-items-center bg-slate-50 text-sm font-bold text-slate-500">Đang kiểm tra phiên đăng nhập...</div>;
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
      <div className="min-h-screen lg:pl-[260px]">
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
          <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div><div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.15em] text-indigo-500"><Sparkles size={14} />Không gian cá nhân</div><h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl">Chào buổi sáng, An! 👋</h1><p className="mt-2 text-sm text-slate-500">Bạn đang có một ngày học tập hiệu quả. Tiếp tục thôi!</p></div>
            <div className="flex items-center gap-2 rounded-xl border border-orange-100 bg-orange-50 px-4 py-2.5 text-xs font-bold text-orange-600"><Flame size={16} fill="currentColor" />12 ngày học liên tiếp</div>
          </section>

          <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard title="Tài liệu đã học" value="24" detail="↗ 3 tài liệu trong tuần này" icon={BookOpen} tone="indigo" />
            <StatCard title="Câu hỏi đã hỏi" value="186" detail="↗ 12% so với tuần trước" icon={MessageSquareText} tone="orange" />
            <StatCard title="Bài đã hoàn thành" value="32" detail="↗ 8 bài trong tuần này" icon={FileText} tone="emerald" />
          </section>

          <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.65fr_1fr]">
            <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
              <div className="mb-2 flex items-start justify-between"><div><h2 className="font-extrabold text-slate-900">Hoạt động học tập</h2><p className="mt-1 text-xs text-slate-400">Thời gian học trong 7 ngày qua</p></div><select aria-label="Khoảng thời gian" className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-500 outline-none"><option>7 ngày qua</option><option>30 ngày qua</option></select></div>
              <WeeklyChart />
            </div>
            <DailyGoal />
          </section>

          <section>
            <div className="mb-4"><h2 className="font-extrabold text-slate-900">Bắt đầu nhanh</h2><p className="mt-1 text-xs text-slate-400">Tính năng bạn có thể sử dụng ngay</p></div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{quickActions.map((item) => <QuickAction key={item.title} item={item} />)}</div>
          </section>

          <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.65fr_1fr]">
            <RecentDocuments />
            <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
              <div className="flex items-center gap-5"><ProgressRing value={72} /><div><p className="text-sm font-extrabold text-slate-900">Mục tiêu tuần</p><p className="mt-1 text-xs leading-5 text-slate-400">Bạn đã hoàn thành 18/25 nhiệm vụ. Còn 3 ngày nữa!</p></div></div>
              <div className="mt-5 flex items-center gap-2 rounded-xl bg-emerald-50 px-4 py-3 text-xs font-semibold text-emerald-700"><Target size={15} />Tiến độ tốt hơn 18% so với tuần trước</div>
            </div>
          </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}


