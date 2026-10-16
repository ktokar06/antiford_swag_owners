import React from 'react';
import { cn } from '@/libs/utils';

const TONES = {
  default: 'text-foreground',
  primary: 'text-primary',
  high: 'text-risk-high',
  medium: 'text-risk-medium',
  low: 'text-risk-low',
};

export default function StatCard({ label, value, hint, icon: Icon, tone = 'default' }) {
  return (
    <div className="rounded-2xl border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
        {Icon && <Icon className="h-4 w-4 shrink-0 text-muted-foreground/70" />}
      </div>
      <p className={cn('mt-3 font-display text-3xl font-semibold tabular-nums tracking-tight', TONES[tone])}>
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}