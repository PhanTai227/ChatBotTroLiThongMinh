import { useMemo, useState } from 'react';
import {
  BookOpen,
  Bot,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Download,
  FileQuestion,
  Filter,
  MessageSquareText,
  MoreHorizontal,
  Search,
  X,
} from 'lucide-react';
import { StatCard } from './DashboardCards';

type ActivityType = 'Tài liệu' | 'Chat AI' | 'Quiz' | 'Bài tập';

type Activity = {
  id: number;
  type: ActivityType;
  title: string;
  detail: string;
  subject: string;
  time: string;
  dateGroup: 'Hôm nay' | 'Hôm qua' | 'Tuần trước';
  duration: string;
  result?: string;
};

const activities: Activity[] = [
  { id: 1, type: 'Chat AI', title: 'Hỏi về Gradient Descent', detail: 'Đã nhận câu trả lời kèm 2 nguồn tham khảo', subject: 'Trí tuệ nhân tạo', time: '14:32', dateGroup: 'Hôm nay', duration: '8 phút' },
  { id: 2, type: 'Quiz', title: 'Ôn tập Gradient Descent', detail: 'Hoàn thành 7/8 câu đúng', subject: 'Thuật toán tối ưu', time: '10:15', dateGroup: 'Hôm nay', duration: '6 phút', result: '87%' },
  { id: 3, type: 'Tài liệu', title: 'Đã tải lên Giáo trình Trí tuệ nhân tạo', detail: 'OCR và tạo vector hoàn tất', subject: 'Trí tuệ nhân tạo', time: '09:48', dateGroup: 'Hôm nay', duration: '3 phút' },
  { id: 4, type: 'Bài tập', title: 'Nộp bài phân tích thuật toán tìm kiếm', detail: 'AI đã nhận xét và góp ý bài làm', subject: 'Thuật toán tối ưu', time: '16:20', dateGroup: 'Hôm qua', duration: '24 phút', result: '8/10' },
  { id: 5, type: 'Chat AI', title: 'So sánh thuật toán tìm kiếm tối ưu', detail: 'Đã hỏi và so sánh 4 thuật toán', subject: 'Thuật toán tối ưu', time: '11:05', dateGroup: 'Hôm qua', duration: '12 phút' },
  { id: 6, type: 'Quiz', title: 'Kiểm tra Chương 1', detail: 'Hoàn thành 18/20 câu đúng', subject: 'Trí tuệ nhân tạo', time: '20:30', dateGroup: 'Tuần trước', duration: '18 phút', result: '90%' },
  { id: 7, type: 'Tài liệu', title: 'Đã tải lên Slide Thuật toán tối ưu', detail: 'Tài liệu đã sẵn sàng để hỏi đáp', subject: 'Thuật toán tối ưu', time: '15:12', dateGroup: 'Tuần trước', duration: '2 phút' },
];

const typeStyle: Record<ActivityType, { icon: typeof Bot; color: string }> = {
  'Chat AI': { icon: Bot, color: 'bg-accent-soft text-accent' },
  Quiz: { icon: FileQuestion, color: 'bg-amber-50 text-amber-700' },
  'Tài liệu': { icon: BookOpen, color: 'bg-sky-50 text-sky-700' },
  'Bài tập': { icon: CheckCircle2, color: 'bg-emerald-50 text-emerald-700' },
};


export function HistoryPage() {
  const [type, setType] = useState('Tất cả');
  const [subject, setSubject] = useState('Tất cả môn học');
  const [period, setPeriod] = useState('Tất cả thời gian');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Activity | null>(null);

  const filtered = useMemo(() => activities.filter((activity) => {
    const matchesType = type === 'Tất cả' || activity.type === type;
    const matchesSubject = subject === 'Tất cả môn học' || activity.subject === subject;
    const matchesSearch = `${activity.title} ${activity.detail}`.toLowerCase().includes(search.toLowerCase());
    const matchesPeriod = period === 'Tất cả thời gian' || (period === '7 ngày qua' && activity.dateGroup !== 'Tuần trước') || period === '30 ngày qua';
    return matchesType && matchesSubject && matchesSearch && matchesPeriod;
  }), [type, subject, search, period]);

  const exportCsv = () => {
    const header = 'Loai,Hoat dong,Mon hoc,Thoi gian,Ket qua\n';
    const rows = filtered.map((item) => [item.type, `"${item.title}"`, item.subject, item.time, item.result ?? ''].join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + header + rows], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'lich-su-hoc-tap.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow text-accent">Theo dõi hoạt động</p>
          <h1 className="page-title mt-2 text-3xl text-ink">Lịch sử học tập</h1>
          <p className="mt-2 text-sm text-muted">Xem lại tài liệu, câu hỏi và bài tập của bạn.</p>
        </div>
        <button onClick={exportCsv} className="btn btn-outline"><Download size={16} />Xuất lịch sử</button>
      </section>
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Hoạt động 7 ngày" value="38" detail="↗ 12% so với tuần trước" icon={CalendarDays} tone="indigo" />
        <StatCard title="Câu hỏi AI" value="24" detail="Tương tác với trợ lý học tập" icon={MessageSquareText} tone="orange" />
        <StatCard title="Quiz hoàn thành" value="8" detail="Điểm trung bình 86%" icon={CheckCircle2} tone="emerald" />
      </section>
      <section className="card p-4 sm:p-5">
        <div className="grid gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div className="relative"><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={16} /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Tìm hoạt động..." className="input input-icon h-12" /></div>
          <label className="flex items-center gap-2 rounded-lg border border-line px-3"><Filter size={15} className="text-muted" /><select aria-label="Loại hoạt động" value={type} onChange={(e) => setType(e.target.value)} className="h-12 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option>Tất cả</option><option>Chat AI</option><option>Quiz</option><option>Tài liệu</option><option>Bài tập</option></select><ChevronDown size={14} /></label>
          <label className="flex items-center gap-2 rounded-lg border border-line px-3"><BookOpen size={15} className="text-muted" /><select aria-label="Môn học" value={subject} onChange={(e) => setSubject(e.target.value)} className="h-12 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option>Tất cả môn học</option><option>Trí tuệ nhân tạo</option><option>Thuật toán tối ưu</option></select><ChevronDown size={14} /></label>
          <label className="flex items-center gap-2 rounded-lg border border-line px-3"><Clock3 size={15} className="text-muted" /><select aria-label="Khoảng thời gian" value={period} onChange={(e) => setPeriod(e.target.value)} className="h-12 min-w-0 flex-1 bg-transparent text-xs font-semibold text-ink outline-none"><option>Tất cả thời gian</option><option>7 ngày qua</option><option>30 ngày qua</option></select><ChevronDown size={14} /></label>
        </div>
      </section>

      {filtered.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line bg-surface py-16 text-center"><Search className="mx-auto text-[#c9c3b6]" size={38} /><p className="mt-3 font-semibold text-ink">Không có lịch sử phù hợp</p><p className="mt-1 text-sm text-muted">Hãy thay đổi điều kiện lọc.</p></div>
      ) : (
        <div className="space-y-6">
          {(['Hôm nay', 'Hôm qua', 'Tuần trước'] as Activity['dateGroup'][]).map((group) => {
            const items = filtered.filter((item) => item.dateGroup === group);
            if (!items.length) return null;
            return (
              <section key={group}>
                <h2 className="eyebrow mb-3 text-muted">{group}</h2>
                <div className="space-y-3">
                  {items.map((activity) => {
                    const style = typeStyle[activity.type];
                    const Icon = style.icon;
                    return (
                      <button key={activity.id} onClick={() => setSelected(activity)} className="card group flex w-full items-center gap-4 p-4 text-left transition hover:border-accent">
                        <div className={`grid size-11 shrink-0 place-items-center rounded-lg ${style.color}`}><Icon size={19} /></div>
                        <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><p className="font-semibold text-ink group-hover:text-accent">{activity.title}</p>{activity.result && <span className="pill bg-emerald-50 text-emerald-700">{activity.result}</span>}</div><p className="mt-1 text-xs text-muted">{activity.detail}</p><div className="mt-2 flex flex-wrap gap-3 text-[10px] font-semibold text-muted"><span>{activity.subject}</span><span className="flex items-center gap-1"><Clock3 size={12} />{activity.duration}</span><span>{activity.time}</span></div></div>
                        <MoreHorizontal size={17} className="text-[#c9c3b6]" />
                      </button>
                    );
                  })}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 z-[70] grid place-items-center bg-ink/45 p-4" onMouseDown={(e) => { if (e.target === e.currentTarget) setSelected(null); }}>
          <div role="dialog" aria-modal="true" className="w-full max-w-md rounded-2xl bg-surface p-6 shadow-2xl">
            <div className="flex items-start justify-between"><div><span className="eyebrow text-accent">{selected.type}</span><h2 className="section-title mt-1 text-xl text-ink">{selected.title}</h2></div><button aria-label="Đóng" onClick={() => setSelected(null)} className="rounded-lg p-2 text-muted hover:bg-[#f1eee6] hover:text-ink"><X size={19} /></button></div>
            <div className="mt-5 space-y-3 rounded-xl bg-paper p-4 text-sm"><div className="flex justify-between"><span className="text-muted">Môn học</span><span className="font-semibold text-ink">{selected.subject}</span></div><div className="flex justify-between"><span className="text-muted">Thời gian</span><span className="font-semibold text-ink">{selected.time} · {selected.duration}</span></div>{selected.result && <div className="flex justify-between"><span className="text-muted">Kết quả</span><span className="font-bold text-emerald-600">{selected.result}</span></div>}</div>
            <p className="mt-4 text-sm leading-6 text-muted">{selected.detail}. Dữ liệu chi tiết sẽ được hiển thị sau khi kết nối backend SQLite.</p>
          </div>
        </div>
      )}
    </>
  );
}

