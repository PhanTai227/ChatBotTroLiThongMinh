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
            <stop offset="0%" stopColor="#6366f1" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.01" />
          </linearGradient>
        </defs>
        {[40, 78, 116, 154].map((y) => <line key={y} x1="30" x2="378" y1={y} y2={y} stroke="#eef2f7" strokeDasharray="4 5" />)}
        <polygon points={areaPoints} fill="url(#activityArea)" />
        <polyline points={points} fill="none" stroke="#6366f1" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {chartData.map((value, index) => {
          const [x, y] = point(index, value).split(',');
          return <circle key={chartLabels[index]} cx={x} cy={y} r={index === 5 ? 5 : 3.5} fill="white" stroke="#6366f1" strokeWidth="2.5" />;
        })}
        {chartLabels.map((label, index) => <text key={label} x={30 + index * 58} y="184" textAnchor="middle" className="fill-slate-400 text-[10px] font-semibold">{label}</text>)}
      </svg>
    </div>
  );
}

export function DailyGoal() {
  return (
    <section className="flex h-full flex-col rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-700 p-6 text-white shadow-xl shadow-indigo-200/50">
      <div className="flex items-center justify-between">
        <div><p className="text-sm font-semibold text-indigo-100">Mục tiêu hôm nay</p><h3 className="mt-1 text-lg font-extrabold">Tập trung 30 phút</h3></div>
        <div className="grid size-11 place-items-center rounded-xl bg-white/10"><Target size={22} /></div>
      </div>
      <div className="my-auto py-5">
        <div className="mb-3 flex items-end justify-between"><span className="text-3xl font-extrabold">18 <small className="text-sm font-medium text-indigo-200">/ 30 phút</small></span><span className="text-xs font-bold text-emerald-200">60%</span></div>
        <div className="h-2 overflow-hidden rounded-full bg-white/15"><div className="h-full w-3/5 rounded-full bg-emerald-300" /></div>
      </div>
      <button className="flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-sm font-extrabold text-indigo-700 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg">
        <Flame size={17} fill="currentColor" />Tiếp tục học <ChevronRight size={17} />
      </button>
    </section>
  );
}
