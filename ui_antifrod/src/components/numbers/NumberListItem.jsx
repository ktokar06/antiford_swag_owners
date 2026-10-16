import React from 'react';
import { Link } from 'react-router-dom';
import { Network } from 'lucide-react';
import { maskNumber, formatNumber, formatPercent } from '@/libs/format';

const Metric = ({ label, value }) => (
  <div>
    <p className="font-mono text-sm tabular-nums">{value}</p>
    <p className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">{label}</p>
  </div>
);

export default function NumberListItem({ record }) {
  const dirs = [
    record.has_incoming && 'входящие',
    record.has_outgoing && 'исходящие',
    record.has_forwarded && 'переадресация',
  ].filter(Boolean);

  return (
    <Link
      to={`/numbers/${record.id}`}
      className="block rounded-2xl border border-border bg-card p-4 transition-colors hover:border-primary/40"
    >
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm">{maskNumber(record.number)}</span>
            {!record.is_valid && (
              <span className="rounded-full border border-risk-high/30 bg-risk-high/10 px-2 py-0.5 text-[11px] text-risk-high">
                невалидные данные
              </span>
            )}
            {record.has_fan_pattern && (
              <span className="inline-flex items-center gap-1 rounded-full border border-risk-high/30 bg-risk-high/10 px-2 py-0.5 text-[11px] text-risk-high">
                <Network className="h-3 w-3" /> веер
              </span>
            )}
          </div>
          <p className="truncate text-sm">{record.subscriber}</p>
          <p className="text-xs text-muted-foreground">
            {record.region} · {record.operator}
          </p>
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {dirs.map((d) => (
              <span key={d} className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
                {d}
              </span>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 text-right">
          <Metric label="вызовов/час" value={formatNumber(record.calls_per_hour)} />
          <Metric label="собеседников" value={formatNumber(record.unique_counterparts)} />
          <Metric label="коротких" value={formatPercent(record.short_call_share)} />
          <Metric label="пик риска" value={formatNumber(record.max_risk_score)} />
        </div>
      </div>
    </Link>
  );
}