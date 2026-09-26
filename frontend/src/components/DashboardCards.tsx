import type { LucideIcon } from 'lucide-react';

export function ProgressRing({ value }: { value: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative size-28 shrink-0">
      <svg className="size-28 -rotate-90" viewBox="0 0 100 100" aria-label={`Tiến độ mục tiêu: ${value}%`}>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#eef2ff" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="#6366f1"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div><span className="text-2xl font-extrabold text-slate-900">{value}%</span><p className="text-[10px] font-semibold text-slate-400">hoàn thành</p></div>
      </div>
    </div>
  );
}

export function StatCard({ title, value, detail, icon: Icon, tone }: { title: string; value: string; detail: string; icon: LucideIcon; tone: 'indigo' | 'orange' | 'emerald' }) {
  const tones = {
    indigo: 'bg-indigo-50 text-indigo-600',
    orange: 'bg-orange-50 text-orange-500',
    emerald: 'bg-emerald-50 text-emerald-600',
  };

  return (
    <article className="rounded-2xl border border-slate-100 bg-white p-5 shadow-[0_4px_20px_rgba(15,23,42,0.035)]">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">{title}</p>
          <p className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900">{value}</p>
        </div>
        <div className={`grid size-11 place-items-center rounded-xl ${tones[tone]}`}><Icon size={21} /></div>
      </div>
      <p className="mt-4 text-xs font-medium text-slate-400">{detail}</p>
    </article>
  );
}
