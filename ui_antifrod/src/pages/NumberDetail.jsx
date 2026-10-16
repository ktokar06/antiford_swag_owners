import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Network } from 'lucide-react';
import { numbersApi, graphApi, callsApi } from '@/api';
import CallListItem from '@/components/calls/CallListItem';
import StatCard from '@/components/stats/StatCard';
import useScoringConfig from '@/hooks/useScoringConfig';
import { maskNumber, formatNumber, formatPercent, formatDateTime, KIND_LABELS } from '@/libs/format';

export default function NumberDetail() {
  const { id } = useParams();
  const { policy } = useScoringConfig();
  const [record, setRecord] = useState(null);
  const [cluster, setCluster] = useState(null);
  const [calls, setCalls] = useState([]);

  useEffect(() => {
    const load = async () => {
      const number = await numbersApi.get(id);
      setRecord(number);
      const page = await callsApi.list({ number_ref: id, sort: '-started_at', limit: 25 });
      setCalls(page.items || []);
      if (number.fan_group) {
        const found = await graphApi.findByLabel(number.fan_group);
        setCluster(found.items?.[0] || null);
      }
    };
    load();
  }, [id]);

  if (!record) {
    return <div className="h-72 animate-pulse rounded-3xl bg-muted" />;
  }

  const dirs = [
    record.has_incoming && 'входящие',
    record.has_outgoing && 'исходящие',
    record.has_forwarded && 'переадресация',
  ].filter(Boolean);

  return (
    <div className="space-y-8">
      <Link to="/numbers" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> К базе номеров
      </Link>

      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-mono text-2xl font-medium sm:text-3xl">{maskNumber(record.number)}</h1>
          {!record.is_valid && (
            <span className="rounded-full border border-risk-high/30 bg-risk-high/10 px-2.5 py-1 text-xs text-risk-high">
              невалидные данные
            </span>
          )}
          {record.has_fan_pattern && (
            <span className="inline-flex items-center gap-1 rounded-full border border-risk-high/30 bg-risk-high/10 px-2.5 py-1 text-xs text-risk-high">
              <Network className="h-3 w-3" /> веер
            </span>
          )}
        </div>
        <p className="text-sm">{record.subscriber}</p>
        <p className="text-xs text-muted-foreground">
          {record.region} · {record.operator} · {KIND_LABELS[record.kind]} ·{' '}
          {dirs.length ? dirs.join(', ') : 'направление не определено'}
        </p>
        {!record.is_valid && (
          <p className="text-xs text-risk-high">
            Причина непригодности: {record.invalid_reason || 'не указана'}
          </p>
        )}
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Вызовов за окно" value={formatNumber(record.total_calls)} hint={`${record.window_days} дней наблюдения`} />
        <StatCard label="Вызовов в час" value={formatNumber(record.calls_per_hour)} hint="пиковая нагрузка" tone="medium" />
        <StatCard label="Уникальных собеседников" value={formatNumber(record.unique_counterparts)} hint={`охват ${formatNumber(record.region_reach)} регионов`} />
        <StatCard label="Пик риска" value={formatNumber(record.max_risk_score)} hint={`средний балл ${formatNumber(record.avg_risk_score)}`} tone="high" />
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-border bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Поведение за окно времени</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Доля коротких вызовов</dt>
              <dd className="font-mono tabular-nums">{formatPercent(record.short_call_share)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Доля неотвеченных</dt>
              <dd className="font-mono tabular-nums">{formatPercent(record.unanswered_share)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Охват регионов</dt>
              <dd className="font-mono tabular-nums">{formatNumber(record.region_reach)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Первый вызов</dt>
              <dd>{formatDateTime(record.first_seen)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Последний вызов</dt>
              <dd>{formatDateTime(record.last_seen)}</dd>
            </div>
          </dl>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Граф связей</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Номеров на абонента</dt>
              <dd className="font-mono tabular-nums">{formatNumber(record.numbers_per_subscriber)}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-muted-foreground">Участие в веере</dt>
              <dd>{record.has_fan_pattern ? 'да' : 'нет'}</dd>
            </div>
          </dl>

          {cluster ? (
            <div className="mt-5 rounded-xl border border-risk-high/25 bg-risk-high/5 p-4">
              <p className="text-sm font-medium">{cluster.label}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{cluster.template}</p>
              <dl className="mt-3 space-y-2 text-xs">
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Номеров в группе</dt>
                  <dd className="font-mono tabular-nums">{formatNumber(cluster.number_count)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Целей обзвона</dt>
                  <dd className="font-mono tabular-nums">{formatNumber(cluster.target_count)}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-muted-foreground">Пересечение списков целей</dt>
                  <dd className="font-mono tabular-nums">{formatPercent(cluster.overlap_share)}</dd>
                </div>
              </dl>
              <Link to="/graph" className="mt-3 inline-block text-xs text-primary">
                Открыть граф связей →
              </Link>
            </div>
          ) : (
            <p className="mt-5 text-xs text-muted-foreground">
              Номер не входит в группы с однотипным обзвоном.
            </p>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-lg font-semibold">Вызовы этого номера</h2>
        <div className="space-y-3">
          {calls.length === 0 && <p className="text-sm text-muted-foreground">Вызовов за окно не найдено.</p>}
          {calls.map((call) => (
            <CallListItem key={call.id} call={call} policy={policy} />
          ))}
        </div>
      </section>
    </div>
  );
}