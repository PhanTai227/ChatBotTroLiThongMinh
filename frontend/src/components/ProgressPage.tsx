import {
  ArrowUpRight,
  Award,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Flame,
  Lightbulb,
  Target,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { ProgressRing, StatCard } from './DashboardCards';

const topics = [
  { name: 'Thuật toán tối ưu', correct: 42, total: 50, score: 84, color: 'bg-indigo-500', change: '+8%' },
  { name: 'Trí tuệ nhân tạo', correct: 68, total: 80, score: 85, color: 'bg-violet-500', change: '+5%' },
  { name: 'Cấu trúc dữ liệu', correct: 31, total: 45, score: 69, color: 'bg-amber-500', change: '-3%' },
  { name: 'Toán rời rạc', correct: 48, total: 55, score: 87, color: 'bg-emerald-500', change: '+10%' },
];

const weekData = [
  { day: 'T2', minutes: 28, questions: 8 },
  { day: 'T3', minutes: 42, questions: 12 },
  { day: 'T4', minutes: 35, questions: 10 },
  { day: 'T5', minutes: 56, questions: 16 },
  { day: 'T6', minutes: 48, questions: 14 },
  { day: 'T7', minutes: 65, questions: 19 },
  { day: 'CN', minutes: 38, questions: 11 },
];

const heatmap = Array.from({ length: 84 }, (_, index) => {
  const active = index % 7 !== 2 || index % 11 === 0;
  return active ? (index % 5 === 0 ? 4 : index % 3 === 0 ? 3 : 2) : 0;
});

const heatClass = ['bg-slate-100', 'bg-indigo-100', 'bg-indigo-300', 'bg-indigo-500', 'bg-indigo-700'];

export function ProgressPage() {
  const maxMinutes = Math.max(...weekData.map((item) => item.minutes));

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-indigo-500">Hành trình của bạn</p><h1 className="text-2xl font-extrabold tracking-tight text-slate-950 sm:text-3xl">Tiến độ học tập</h1><p className="mt-2 text-sm text-slate-500">Theo dõi điểm mạnh, điểm yếu và mức độ hoàn thành mục tiêu.</p></div>
        <label className="flex w-fit items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-bold text-slate-600"><span>30 ngày gần nhất</span><ChevronDown size={16} /></label>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tổng thời gian học" value="18.5h" detail="↗ 2.4h so với tháng trước" icon={Clock3} tone="indigo" />
        <StatCard title="Điểm trung bình" value="84%" detail="↗ 5% so với tháng trước" icon={TrendingUp} tone="emerald" />
        <StatCard title="Chuỗi học tập" value="12 ngày" detail="Kỷ lục: 18 ngày" icon={Flame} tone="orange" />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
          <div className="flex items-center justify-between"><div><h2 className="font-extrabold text-slate-900">Thời gian học trong tuần</h2><p className="mt-1 text-xs text-slate-400">Tổng cộng 5 giờ 12 phút</p></div><span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-[10px] font-extrabold text-emerald-600">↗ 18%</span></div>
          <div className="mt-7 flex h-52 items-end gap-3 sm:gap-5">
            {weekData.map((item, index) => <div key={item.day} className="flex h-full flex-1 flex-col items-center justify-end"><div className="group relative flex w-full flex-1 items-end"><div className={`w-full rounded-t-xl transition hover:opacity-80 ${index === 5 ? 'bg-indigo-600' : 'bg-indigo-200'}`} style={{ height: `${(item.minutes / maxMinutes) * 100}%` }}><span className="absolute -top-7 left-1/2 hidden -translate-x-1/2 rounded bg-slate-900 px-2 py-1 text-[9px] font-bold text-white group-hover:block">{item.minutes} phút</span></div></div><span className="mt-3 text-[10px] font-bold text-slate-400">{item.day}</span></div>)}
          </div>
        </div>

        <div className="rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 p-6 text-white shadow-xl shadow-indigo-200">
          <div className="flex items-center justify-between"><div><p className="text-sm font-semibold text-indigo-100">Mục tiêu tháng</p><h2 className="mt-1 text-xl font-extrabold">Đang đi tốt!</h2></div><div className="grid size-11 place-items-center rounded-xl bg-white/10"><Target size={22} /></div></div>
          <div className="my-7 flex items-center justify-center"><div className="relative grid size-36 place-items-center rounded-full border-[12px] border-white/15"><div className="absolute inset-[-12px] rounded-full border-[12px] border-transparent border-r-indigo-300 border-t-indigo-300 rotate-45" /><div className="text-center"><p className="text-3xl font-extrabold">72%</p><p className="text-[10px] text-indigo-200">đã hoàn thành</p></div></div></div>
          <div className="flex justify-between text-xs"><span className="text-indigo-200">18 giờ / 25 giờ</span><span className="font-bold text-emerald-200">Còn 7 giờ</span></div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.45fr_1fr]">
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="font-extrabold text-slate-900">Tiến độ theo chủ đề</h2><p className="mt-1 text-xs text-slate-400">Dựa trên kết quả quiz và bài tập</p></div><button className="text-xs font-bold text-indigo-600">Xem chi tiết</button></div>
          <div className="space-y-5">
            {topics.map((topic) => <div key={topic.name}><div className="mb-2 flex items-center justify-between"><div><p className="text-sm font-extrabold text-slate-700">{topic.name}</p><p className="mt-0.5 text-[10px] text-slate-400">{topic.correct}/{topic.total} câu đúng</p></div><div className="flex items-center gap-2"><span className={`text-[10px] font-extrabold ${topic.change.startsWith('+') ? 'text-emerald-600' : 'text-rose-500'}`}>{topic.change}</span><span className="w-10 text-right text-sm font-extrabold text-slate-700">{topic.score}%</span></div></div><div className="h-2 overflow-hidden rounded-full bg-slate-100"><div className={`h-full rounded-full ${topic.color}`} style={{ width: `${topic.score}%` }} /></div></div>)}
          </div>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
          <h2 className="font-extrabold text-slate-900">Nhận diện điểm mạnh/yếu</h2><p className="mt-1 text-xs text-slate-400">Gợi ý dựa trên hoạt động gần đây</p>
          <div className="mt-5 space-y-3"><div className="rounded-2xl bg-emerald-50 p-4"><div className="flex items-center gap-2 text-sm font-extrabold text-emerald-700"><CheckCircle2 size={18} />Điểm mạnh</div><p className="mt-2 text-xs leading-5 text-emerald-700/80">Bạn hiểu tốt về Toán rời rạc và kiến thức nền của Trí tuệ nhân tạo.</p></div><div className="rounded-2xl bg-rose-50 p-4"><div className="flex items-center gap-2 text-sm font-extrabold text-rose-700"><Lightbulb size={18} />Cần cải thiện</div><p className="mt-2 text-xs leading-5 text-rose-700/80">Kết quả Cấu trúc dữ liệu đang giảm. Nên ôn lại cây nhị phân và giải pháp đệ quy.</p></div><div className="rounded-2xl bg-indigo-50 p-4"><div className="flex items-center gap-2 text-sm font-extrabold text-indigo-700"><BrainCircuit size={18} />Gợi ý cho bạn</div><p className="mt-2 text-xs leading-5 text-indigo-700/80">Dành 20 phút ôn Cấu trúc dữ liệu và làm một bài quiz ngắng vào tối nay.</p></div></div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
          <h2 className="font-extrabold text-slate-900">Lịch học 12 tuần</h2><p className="mt-1 text-xs text-slate-400">Số ô càng đậm thì thời gian học càng nhiều</p>
          <div className="mt-5 overflow-x-auto"><div className="grid min-w-[560px] grid-flow-col grid-rows-7 gap-1.5">{heatmap.map((level, index) => <div key={index} title={`Ngày ${index + 1}`} className={`size-4 rounded ${heatClass[level]}`} />)}</div><div className="mt-4 flex items-center justify-between text-[10px] text-slate-400"><span>12 tuần trước</span><div className="flex items-center gap-1">Ít hơn <span className="size-3 rounded bg-slate-100" /><span className="size-3 rounded bg-indigo-200" /><span className="size-3 rounded bg-indigo-400" /><span className="size-3 rounded bg-indigo-700" /> Nhiều hơn</div><span>Hôm nay</span></div></div>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)] sm:p-6">
          <div className="flex items-center gap-5"><ProgressRing value={72} /><div><h2 className="font-extrabold text-slate-900">Cấp độ học viên</h2><p className="mt-1 text-xs text-slate-400">Bạn đang ở hạng Bạc</p></div></div>
          <div className="mt-5 rounded-2xl bg-amber-50 p-4"><div className="flex items-center justify-between text-xs font-extrabold text-amber-700"><span className="flex items-center gap-2"><Award size={17} />Hạng Bạc</span><span>1.250 / 2.000 XP</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-amber-100"><div className="h-full w-[62%] rounded-full bg-amber-500" /></div></div>
          <button className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-indigo-200 py-3 text-xs font-extrabold text-indigo-600 hover:bg-indigo-50"><Trophy size={16} />Xem tất cả thành tích</button>
        </div>
      </section>
    </>
  );
}
