import React from 'react';
import { riskLevelFromScore } from '@/libs/scoring';
import { cn } from '@/libs/utils';

const TONE = {
  low: 'border-risk-low/30 bg-risk-low/10 text-risk-low',
  medium: 'border-risk-medium/30 bg-risk-medium/10 text-risk-medium',
  high: 'border-risk-high/30 bg-risk-high/10 text-risk-high',
};

export default function ScoreBadge({ score = 0, policy, size = 'md' }) {
  const level = riskLevelFromScore(score, policy);
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-baseline gap-1 rounded-full border font-mono tabular-nums',
        TONE[level],
        size === 'lg' ? 'px-5 py-2 text-3xl' : 'px-2.5 py-1 text-xs'
      )}
    >
      {score}
      <span className={cn('font-body font-normal opacity-60', size === 'lg' ? 'text-sm' : 'text-[10px]')}>
        из 100
      </span>
    </span>
  );
}