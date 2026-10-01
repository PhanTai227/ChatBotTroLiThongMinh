import {
  Award,
  BrainCircuit,
  CheckCircle2,
  Clock3,
  Flame,
  Lightbulb,
  Target,
  TrendingUp,
  Trophy,
} from 'lucide-react';
import { ProgressRing, StatCard } from './DashboardCards';

const topics = [
  { name: 'Thuật toán tối ưu', correct: 42, total: 50, score: 84, color: 'bg-accent', change: '+8%' },
  { name: 'Trí tuệ nhân tạo', correct: 68, total: 80, score: 85, color: 'bg-sky-500', change: '+5%' },
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

const heatClass = ['bg-[#efece3]', 'bg-accent-soft', 'bg-[#9fc4ae]', 'bg-accent', 'bg-accent-deep'];

export function ProgressPage() {
  const maxMinutes = Math.max(...weekData.map((item) => item.minutes));

  return (
    <>
      <section className="animate-fade-up flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="eyebrow text-accent">Hành trình của bạn</p>
          <h1 className="page-title mt-2 text-3xl text-ink">Tiến độ học tập</h1>
          <p className="mt-2 text-sm text-muted">Theo dõi điểm mạnh, điểm yếu và mức độ hoàn thành mục tiêu.</p>
        </div>
        <span className="flex w-fit items-center gap-2 rounded-lg border border-line bg-surface px-4 py-3 text-sm font-semibold text-muted"><span>30 ngày gần nhất</span></span>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatCard title="Tổng thời gian học" value="18.5h" detail="↗ 2.4h so với tháng trước" icon={Clock3} tone="indigo" />
        <StatCard title="Điểm trung bình" value="84%" detail="↗ 5% so với tháng trước" icon={TrendingUp} tone="emerald" />
        <StatCard title="Chuỗi học tập" value="12 ngày" detail="Kỷ lục: 18 ngày" icon={Flame} tone="orange" />
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.6fr_1fr]">
        <div className="card p-5 sm:p-6">
          <div className="flex items-center justify-between"><div><h2 className="section-title text-ink">Thời gian học trong tuần</h2><p className="mt-1 text-xs text-muted">Tổng cộng 5 giờ 12 phút</p></div><span className="rounded-md bg-emerald-50 px-2.5 py-1 text-[10px] font-bold text-emerald-700">↗ 18%</span></div>
          <div className="mt-7 flex h-52 items-end gap-3 sm:gap-5">
            {weekData.map((item, index) => <div key={item.day} className="flex h-full flex-1 flex-col items-center justify-end"><div className="group relative flex w-full flex-1 items-end"><div className={`w-full rounded-t-md transition hover:opacity-80 ${index === 5 ? 'bg-accent' : 'bg-[#b9d3c5]'}`} style={{ height: `${(item.minutes / maxMinutes) * 100}%` }}><span className="absolute -top-7 left-1/2 hidden -translate-x-1/2 rounded bg-ink px-2 py-1 text-[9px] font-bold text-white group-hover:block">{item.minutes} phút</span></div></div><span className="mt-3 text-[10px] font-bold text-muted">{item.day}</span></div>)}
          </div>
        </div>

        <div className="rounded-2xl bg-accent p-6 text-white">
          <div className="flex items-center justify-between"><div><p className="text-sm font-medium text-white/70">Mục tiêu tháng</p><h2 className="section-title mt-1 text-xl text-white">Đang đi tốt!</h2></div><div className="grid size-10 place-items-center rounded-lg bg-white/15"><Target size={19} /></div></div>
          <div className="my-7 flex items-center justify-center"><div className="relative grid size-36 place-items-center rounded-full border-[12px] border-white/15"><div className="absolute inset-[-12px] rounded-full border-[12px] border-transparent border-r-white border-t-white rotate-45" /><div className="text-center"><p className="stat-value text-3xl">72%</p><p className="text-[10px] text-white/60">đã hoàn thành</p></div></div></div>
          <div className="flex justify-between text-xs"><span className="text-white/70">18 giờ / 25 giờ</span><span className="font-bold text-white">Còn 7 giờ</span></div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 xl:grid-cols-[1.45fr_1fr]">
        <div className="card p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between"><div><h2 className="section-title text-ink">Tiến độ theo chủ đề</h2><p className="mt-1 text-xs text-muted">Dựa trên kết quả quiz và bài tập</p></div><button className="text-xs font-semibold text-accent">Xem chi tiết</button></div>
          <div className="space-y-5">
            {topics.map((topic) => <div key={topic.name}><div className="mb-2 flex items-center justify-between"><div><p className="text-sm font-semibold text-ink">{topic.name}</p><p className="mt-0.5 text-[10px] text-muted">{topic.correct}/{topic.total} câu đúng</p></div><div className="flex items-center gap-2"><span className={`text-[10px] font-bold ${topic.change.startsWith('+') ? 'text-emerald-600' : 'text-rose-500'}`}>{topic.change}</span><span className="w-10 text-right text-sm font-semibold text-ink">{topic.score}%</span></div></div><div className="h-2 overflow-hidden rounded-full bg-[#efece3]"><div className={`h-full rounded-full ${topic.color}`} style={{ width: `${topic.score}%` }} /></div></div>)}
          </div>
        </div>
        <div className="card p-5 sm:p-6">
          <h2 className="section-title text-ink">Nhận diện điểm mạnh/yếu</h2><p className="mt-1 text-xs text-muted">Gợi ý dựa trên hoạt động gần đây</p>
          <div className="mt-5 space-y-3"><div className="rounded-xl bg-emerald-50 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-emerald-700"><CheckCircle2 size={17} />Điểm mạnh</div><p className="mt-2 text-xs leading-5 text-emerald-700/80">Bạn hiểu tốt về Toán rời rạc và kiến thức nền của Trí tuệ nhân tạo.</p></div><div className="rounded-xl bg-rose-50 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-rose-700"><Lightbulb size={17} />Cần cải thiện</div><p className="mt-2 text-xs leading-5 text-rose-700/80">Kết quả Cấu trúc dữ liệu đang giảm. Nên ôn lại cây nhị phân và giải pháp đệ quy.</p></div><div className="rounded-xl bg-accent-soft p-4"><div className="flex items-center gap-2 text-sm font-semibold text-accent"><BrainCircuit size={17} />Gợi ý cho bạn</div><p className="mt-2 text-xs leading-5 text-accent/80">Dành 20 phút ôn Cấu trúc dữ liệu và làm một bài quiz ngắn vào tối nay.</p></div></div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="card p-5 sm:p-6">
          <h2 className="section-title text-ink">Lịch học 12 tuần</h2><p className="mt-1 text-xs text-muted">Số ô càng đậm thì thời gian học càng nhiều</p>
          <div className="mt-5 overflow-x-auto"><div className="grid min-w-[560px] grid-flow-col grid-rows-7 gap-1.5">{heatmap.map((level, index) => <div key={index} title={`Ngày ${index + 1}`} className={`size-4 rounded ${heatClass[level]}`} />)}</div><div className="mt-4 flex items-center justify-between text-[10px] text-muted"><span>12 tuần trước</span><div className="flex items-center gap-1">Ít hơn <span className="size-3 rounded bg-[#efece3]" /><span className="size-3 rounded bg-accent-soft" /><span className="size-3 rounded bg-[#9fc4ae]" /><span className="size-3 rounded bg-accent" /> Nhiều hơn</div><span>Hôm nay</span></div></div>
        </div>
        <div className="card p-5 sm:p-6">
          <div className="flex items-center gap-5"><ProgressRing value={72} /><div><h2 className="section-title text-ink">Cấp độ học viên</h2><p className="mt-1 text-xs text-muted">Bạn đang ở hạng Bạc</p></div></div>
          <div className="mt-5 rounded-xl bg-amber-50 p-4"><div className="flex items-center justify-between text-xs font-bold text-amber-800"><span className="flex items-center gap-2"><Award size={16} />Hạng Bạc</span><span>1.250 / 2.000 XP</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-amber-100"><div className="h-full w-[62%] rounded-full bg-amber-500" /></div></div>
          <button className="btn btn-outline mt-4 w-full py-3 text-xs"><Trophy size={15} />Xem tất cả thành tích</button>
        </div>
      </section>
    </>
  );
}
