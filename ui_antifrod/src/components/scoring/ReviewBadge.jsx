import React from 'react';
import { REVIEW_META } from '@/libs/scoring';
import { cn } from '@/libs/utils';

export default function ReviewBadge({ status = 'pending', className }) {
  const meta = REVIEW_META[status] || REVIEW_META.pending;
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-medium',
        meta.badge,
        className
      )}
    >
      {meta.label}
    </span>
  );
}