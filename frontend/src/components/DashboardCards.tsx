import type { LucideIcon } from 'lucide-react';

export function ProgressRing({ value }: { value: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (value / 100) * circumference;

  return (
    <div className="relative size-28 shrink-0">
      <svg className="size-28 -rotate-90" viewBox="0 0 100 100" aria-label={`Tiến độ mục tiêu: ${value}%`}>
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#e9f0ea" strokeWidth="8" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke="#1d6b45"
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div><span className="stat-value text-2xl">{value}%</span><p className="text-[10px] font-semibold text-muted">hoàn thành</p></div>
      </div>
    </div>
  );
}

export function StatCard({ title, value, detail, icon: Icon, tone }: { title: string; value: string; detail: string; icon: LucideIcon; tone: 'indigo' | 'orange' | 'emerald' }) {
  const tones = {
    indigo: 'bg-accent-soft text-accent',
    orange: 'bg-amber-50 text-amber-700',
    emerald: 'bg-emerald-50 text-emerald-700',
  };

  return (
    <article className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-muted">{title}</p>
          <p className="stat-value mt-2 text-3xl">{value}</p>
        </div>
        <div className={`grid size-10 shrink-0 place-items-center rounded-lg ${tones[tone]}`}><Icon size={19} /></div>
      </div>
      <p className="mt-3 text-xs text-muted">{detail}</p>
    </article>
  );
}
