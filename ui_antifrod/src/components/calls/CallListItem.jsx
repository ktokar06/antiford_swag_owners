import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Globe } from 'lucide-react';
import ScoreBadge from '@/components/scoring/ScoreBadge';
import DecisionBadge from '@/components/scoring/DecisionBadge';
import { maskNumber, formatDateTime, formatDuration, DIRECTION_LABELS } from '@/libs/format';

export default function CallListItem({ call, policy }) {

  return (
    <Link
      to={`/calls/${call.id}`}
      className="block rounded-2xl border border-border bg-card p-4 transition-colors hover:border-primary/40"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <div className="flex flex-wrap items-center gap-2 font-mono text-sm">
            <span>{maskNumber(call.caller)}</span>
            <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" />
            <span>{maskNumber(call.callee)}</span>
          </div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span>{formatDateTime(call.started_at)}</span>
            <span>· {formatDuration(call.duration_sec)}</span>
            <span>· {DIRECTION_LABELS[call.direction]}</span>
            {call.foreign_origin && (
              <span className="inline-flex items-center gap-1 text-risk-medium">
                <Globe className="h-3 w-3" /> вход из-за рубежа
              </span>
            )}
            {call.hung_up_first_second && (
              <span className="text-risk-high">· отбой на первой секунде</span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            <span className="text-foreground">{call.probability == null ? 'Ожидает ML-оценки' : `CatBoost · вероятность ${(call.probability * 100).toFixed(2)}% · SHAP в карточке`}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <ScoreBadge score={call.risk_score} policy={policy} />
          <DecisionBadge decision={call.decision} />
        </div>
      </div>
    </Link>
  );
}
