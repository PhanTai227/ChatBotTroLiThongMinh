import { ChevronRight, Flame, Target } from 'lucide-react';
import { chartData, chartLabels } from '../data';

function point(index: number, value: number) {
  const x = 30 + index * 58;
  const y = 150 - ((value - 30) / 70) * 115;
  return `${x},${y}`;
}

const points = chartData.map(point).join(' ');
const areaPoints = `30,160 ${points} 378,160`;

export function WeeklyChart() {
  return (
    <div className="h-[205px] w-full">
      <svg viewBox="0 0 410 190" className="h-full w-full overflow-visible" role="img" aria-label="Biểu đồ hoạt động học tập trong bảy ngày">
        <defs>
          <linearGradient id="activityArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1d6b45" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#1d6b45" stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {[40, 78, 116, 154].map((y) => <line key={y} x1="30" x2="378" y1={y} y2={y} stroke="#e6e2d8" strokeDasharray="4 5" />)}
        <polygon points={areaPoints} fill="url(#activityArea)" />
        <polyline points={points} fill="none" stroke="#1d6b45" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {chartData.map((value, index) => {
          const [x, y] = point(index, value).split(',');
          return <circle key={chartLabels[index]} cx={x} cy={y} r={index === 5 ? 5 : 3.5} fill="white" stroke="#1d6b45" strokeWidth="2.5" />;
        })}
        {chartLabels.map((label, index) => <text key={label} x={30 + index * 58} y="184" textAnchor="middle" className="fill-muted text-[10px] font-semibold">{label}</text>)}
      </svg>
    </div>
  );
}

export function DailyGoal() {
  return (
    <section className="flex h-full flex-col rounded-2xl bg-accent p-6 text-white">
      <div className="flex items-center justify-between">
        <div><p className="text-sm font-medium text-white/70">Mục tiêu hôm nay</p><h3 className="section-title mt-1 text-lg text-white">Tập trung 30 phút</h3></div>
        <div className="grid size-10 place-items-center rounded-lg bg-white/15"><Target size={20} /></div>
      </div>
      <div className="my-auto py-5">
        <div className="mb-3 flex items-end justify-between">
          <span className="stat-value text-3xl">18 <small className="text-sm font-medium text-white/60">/ 30 phút</small></span>
          <span className="text-xs font-bold text-white/80">60%</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-white/20"><div className="h-full w-3/5 rounded-full bg-white" /></div>
      </div>
      <button className="flex w-full items-center justify-center gap-2 rounded-lg bg-white px-4 py-3 text-sm font-semibold text-accent transition hover:bg-accent-soft">
        <Flame size={16} />Tiếp tục học <ChevronRight size={16} />
      </button>
    </section>
  );
}
