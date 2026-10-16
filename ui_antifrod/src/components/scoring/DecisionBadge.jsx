import React from 'react';
import { DECISION_META } from '@/libs/scoring';
import { cn } from '@/libs/utils';

export default function DecisionBadge({ decision = 'allow', className }) {
  const meta = DECISION_META[decision] || DECISION_META.allow;
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-medium uppercase tracking-[0.08em]',
        meta.badge,
        className
      )}
    >
      {meta.label}
    </span>
  );
}