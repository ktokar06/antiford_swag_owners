import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Network, AlertTriangle } from 'lucide-react';
import { graphApi, numbersApi } from '@/api';
import { formatNumber, formatPercent, maskNumber } from '@/libs/format';
import { cn } from '@/libs/utils';

const RISK_TONE = {
  high: 'border-risk-high/30 bg-risk-high/10 text-risk-high',
  medium: 'border-risk-medium/30 bg-risk-medium/10 text-risk-medium',
  low: 'border-risk-low/30 bg-risk-low/10 text-risk-low',
};

export default function GraphView() {
  const [clusters, setClusters] = useState([]);
  const [subscribers, setSubscribers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      graphApi.listClusters({ sort: '-number_count', limit: 50 }),
      numbersApi.aggregateBySubscriber(),
    ]).then(([page, aggregateResult]) => {
      setClusters(page.items || []);
      setSubscribers((aggregateResult?.rows || []).filter((row) => row.count > 1));
      setLoading(false);
    });
  }, []);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Граф связей</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Веера и абоненты</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Веер — группа номеров, которая обзванивает непересекающиеся списки адресатов по одному шаблону:
          одинаковая длительность, одинаковые часы, одинаковая доля неотвеченных.
        </p>
      </header>

      {loading && <div className="h-64 animate-pulse rounded-3xl bg-muted" />}

      <section className="space-y-4">
        {!loading && clusters.length === 0 && (
          <p className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Групп с однотипным обзвоном не обнаружено.
          </p>
        )}
        {clusters.map((cluster) => (
          <article key={cluster.id} className="rounded-2xl border border-border bg-card p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Network className="h-4 w-4 text-risk-high" />
                  <h2 className="font-display text-lg font-semibold">{cluster.label}</h2>
                  <span
                    className={cn(
                      'rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-[0.08em]',
                      RISK_TONE[cluster.risk_level] || RISK_TONE.low
                    )}
                  >
                    {cluster.pattern === 'fan' ? 'веер' : cluster.pattern}
                  </span>
                </div>
                <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{cluster.template}</p>
              </div>
              <dl className="grid grid-cols-3 gap-5 text-right">
                <div>
                  <dd className="font-mono text-sm tabular-nums">{formatNumber(cluster.number_count)}</dd>
                  <dt className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">номеров</dt>
                </div>
                <div>
                  <dd className="font-mono text-sm tabular-nums">{formatNumber(cluster.target_count)}</dd>
                  <dt className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">целей</dt>
                </div>
                <div>
                  <dd className="font-mono text-sm tabular-nums">{formatPercent(cluster.overlap_share)}</dd>
                  <dt className="text-[10px] uppercase tracking-[0.1em] text-muted-foreground">пересечение</dt>
                </div>
              </dl>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {(cluster.numbers || []).map((n) => (
                <span key={n} className="rounded-lg border border-border px-2 py-1 font-mono text-xs">
                  {maskNumber(n)}
                </span>
              ))}
            </div>

            <p className="mt-4 text-xs text-muted-foreground">
              Регионы обзвона: {(cluster.regions || []).join(', ')}
            </p>
          </article>
        ))}
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-lg font-semibold">Абоненты с несколькими номерами</h2>
        <div className="overflow-hidden rounded-2xl border border-border bg-card">
          {subscribers.length === 0 && !loading && (
            <p className="p-6 text-sm text-muted-foreground">
              На каждого абонента оформлено по одному номеру.
            </p>
          )}
          {subscribers.map((row) => (
            <div
              key={row.subscriber}
              className="flex items-center justify-between gap-4 border-b border-border px-5 py-3.5 last:border-0"
            >
              <div className="min-w-0">
                <p className="truncate text-sm">{row.subscriber}</p>
                <p className="text-xs text-muted-foreground">номеров на абонента</p>
              </div>
              <div className="flex items-center gap-4">
                <span className="font-mono text-sm tabular-nums">{formatNumber(row.count)}</span>
                {row.count >= 4 && <AlertTriangle className="h-3.5 w-3.5 text-risk-high" />}
              </div>
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Много номеров на одного абонента — самостоятельный признак, который входит в скоринг отдельным фактором.{' '}
          <Link to="/numbers" className="text-primary">
            Открыть базу номеров →
          </Link>
        </p>
      </section>
    </div>
  );
}