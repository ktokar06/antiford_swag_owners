import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Hash, CalendarDays, Ban, ShieldCheck, AlertTriangle, Network, FileText } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { callsApi, statsApi } from '@/api';
import StatCard from '@/components/stats/StatCard';
import CallListItem from '@/components/calls/CallListItem';
import useScoringConfig from '@/hooks/useScoringConfig';
import { formatNumber, formatPeriod, formatDay, DIRECTION_LABELS } from '@/libs/format';

const tooltipStyle = {
  contentStyle: {
    borderRadius: 12,
    border: '1px solid hsl(var(--border))',
    background: 'hsl(var(--card))',
    fontSize: 12,
  },
  labelStyle: { color: 'hsl(var(--muted-foreground))' },
};

const axis = { tickLine: false, axisLine: false, fontSize: 11, stroke: 'hsl(var(--muted-foreground))' };

const SERIES = {
  allow: { label: 'пропущено', color: 'hsl(var(--risk-low))' },
  review: { label: 'на проверку', color: 'hsl(var(--risk-medium))' },
  blocked: { label: 'автоблокировка', color: 'hsl(var(--risk-high))' },
};

function ChartCard({ title, hint, children, className = '' }) {
  return (
    <section className={`rounded-2xl border border-border bg-card p-6 ${className}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-lg font-semibold">{title}</h2>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <div className="mt-6 h-56 w-full">{children}</div>
    </section>
  );
}

export default function Dashboard() {
  const { policy } = useScoringConfig();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      statsApi.summary(),
      statsApi.daily(),
      statsApi.hourly(),
      statsApi.scoreDistribution(),
      statsApi.invalidReasons(),
      statsApi.directions(),
      statsApi.factors(),
      callsApi.list({ decision: 'auto_blocked', sort: '-started_at', limit: 4 }),
    ])
      .then(([summary, daily, hourly, scores, reasons, directions, factors, recent]) =>
        setData({
          summary,
          daily: daily.rows.map((r) => ({ ...r, label: formatDay(r.day) })),
          hourly: hourly.rows.map((r) => ({ ...r, label: `${String(r.hour).padStart(2, '0')}:00` })),
          scores: scores.rows,
          reasons: reasons.rows,
          directions: directions.rows,
          factors: factors.rows.slice(0, 8),
          recent: recent.items || [],
        })
      )
      .catch((e) => setError(e.message || 'Не удалось загрузить статистику'));
  }, []);

  if (error) {
    return <p className="rounded-2xl border border-risk-high/30 bg-risk-high/5 p-6 text-sm text-risk-high">{error}</p>;
  }
  if (!data) {
    return <div className="h-72 animate-pulse rounded-3xl bg-muted" />;
  }

  const s = data.summary;
  const period = formatPeriod(s.period_from, s.period_to);

  if (s.calls_total === 0) {
    return (
      <div className="space-y-4 rounded-2xl border border-border bg-card p-8">
        <h1 className="font-display text-2xl font-semibold">Данных пока нет</h1>
        <p className="text-sm text-muted-foreground">
          В базе нет ни одного вызова. Загрузите файлы CDR на странице{' '}
          <Link to="/cdr" className="text-primary">«Записи CDR»</Link> или запустите импорт каталога CDR_OUT.
        </p>
        {s.rows_invalid > 0 && (
          <p className="text-sm text-risk-high">Невалидных строк: {formatNumber(s.rows_invalid)}.</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Обзор базы</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Что есть в данных</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Валидных вызовов: <span className="text-foreground">{formatNumber(s.calls_total)}</span> за период{' '}
          <span className="text-foreground">{period}</span>, загружено из {formatNumber(s.files)} файлов.
          {s.calls_unscored > 0 && ` Ещё не оценено: ${formatNumber(s.calls_unscored)}.`}
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Номеров в базе" value={formatNumber(s.numbers_total)} hint="все стороны вызовов" icon={Hash} />
        <StatCard label="Дней с данными" value={formatNumber(data.daily.length)} hint={period} icon={CalendarDays} />
        <StatCard label="Вызовов" value={formatNumber(s.calls_total)} hint={`средний балл ${s.avg_risk_score}`} icon={ShieldCheck} />
        <StatCard label="Вееров в графе" value={formatNumber(s.clusters)} hint={`${formatNumber(s.numbers_in_fans)} номеров в группах`} icon={Network} tone="high" />
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Автоблокировка" value={formatNumber(s.calls_blocked)} hint={`${formatNumber(s.numbers_blocked)} номеров`} tone="high" icon={Ban} />
        <StatCard label="На проверку" value={formatNumber(s.calls_review)} hint={`ожидают разбора: ${formatNumber(s.reviews_pending)}`} tone="medium" />
        <StatCard label="Пропущено" value={formatNumber(s.calls_allow)} hint="ниже порога проверки" tone="low" />
      </section>

      <ChartCard
        title="Вызовы по дням"
        hint={`пороги: проверка ${policy.review_threshold}, автоблокировка ${policy.auto_block_threshold}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data.daily}>
            <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
            <XAxis dataKey="label" minTickGap={20} {...axis} />
            <YAxis width={48} {...axis} tickFormatter={formatNumber} />
            <Tooltip {...tooltipStyle} formatter={(v, name) => [formatNumber(v), SERIES[name]?.label || name]} />
            <Legend formatter={(name) => SERIES[name]?.label || name} wrapperStyle={{ fontSize: 12 }} />
            {['allow', 'review', 'blocked'].map((k) => (
              <Bar key={k} dataKey={k} stackId="d" fill={SERIES[k].color} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Время суток" hint="вызовы по часам начала">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.hourly}>
              <XAxis dataKey="label" interval={2} {...axis} />
              <YAxis width={48} {...axis} tickFormatter={formatNumber} />
              <Tooltip {...tooltipStyle} formatter={(v, name) => [formatNumber(v), name === 'calls' ? 'вызовов' : SERIES[name]?.label]} />
              <Bar dataKey="calls" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Распределение балла риска" hint="число вызовов по диапазонам">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.scores}>
              <XAxis dataKey="bucket" {...axis} />
              <YAxis width={48} {...axis} tickFormatter={formatNumber} />
              <Tooltip {...tooltipStyle} formatter={(v) => [formatNumber(v), 'вызовов']} />
              <Bar dataKey="calls" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-6 lg:col-span-2">
          <h2 className="font-display text-lg font-semibold">Важность признаков CatBoost</h2>
          <p className="mt-1 text-xs text-muted-foreground">глобальная важность при обучении; индивидуальные SHAP-вклады — в карточке вызова</p>
          <ul className="mt-5 space-y-3">
            {data.factors.length === 0 && <li className="text-sm text-muted-foreground">Факторы не сработали.</li>}
            {data.factors.map((f) => {
               const share = Number(f.points);
              return (
                <li key={f.code} className="space-y-1.5">
                  <div className="flex items-baseline justify-between gap-3 text-sm">
                    <span>{f.label}</span>
                    <span className="font-mono tabular-nums">
                       <span className="text-muted-foreground">{share.toFixed(2)}%</span>
                    </span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                    <div className="h-full rounded-full bg-primary/70" style={{ width: `${Math.min(100, share)}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
          <div className="mt-6 flex flex-wrap gap-4 border-t border-border pt-4 text-xs text-muted-foreground">
            {data.directions.map((d) => (
              <span key={d.direction}>
                {DIRECTION_LABELS[d.direction] || d.direction}:{' '}
                <span className="font-mono text-foreground">{formatNumber(d.calls)}</span>
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Качество данных</h2>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Строк в файлах</dt>
              <dd className="font-mono tabular-nums">{formatNumber(s.rows_total)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Дубликатов отброшено</dt>
              <dd className="font-mono tabular-nums">{formatNumber(s.rows_duplicate)}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Невалидных строк</dt>
              <dd className="font-mono tabular-nums text-risk-high">{formatNumber(s.rows_invalid)}</dd>
            </div>
          </dl>
          {data.reasons.length > 0 ? (
            <>
              <p className="mt-5 flex items-center gap-2 text-xs uppercase tracking-[0.1em] text-muted-foreground">
                <AlertTriangle className="h-3.5 w-3.5" /> Причины
              </p>
              <ul className="mt-2 space-y-2">
                {data.reasons.map((r) => (
                  <li key={r.code} className="flex items-baseline justify-between gap-3 text-sm">
                    <Link to={`/cdr?tab=invalid&error_code=${r.code}`} className="text-muted-foreground hover:text-primary">
                      {r.label}
                    </Link>
                    <span className="font-mono tabular-nums">{formatNumber(r.count)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">Невалидных строк нет.</p>
          )}
          <Link to="/cdr" className="mt-5 inline-flex items-center gap-1 text-xs text-primary">
            <FileText className="h-3 w-3" /> Все записи CDR →
          </Link>
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex items-baseline justify-between">
          <h2 className="font-display text-lg font-semibold">Последние автоблокировки</h2>
          <Link to="/blocks" className="text-xs text-primary">Весь журнал →</Link>
        </div>
        <div className="space-y-3">
          {data.recent.length === 0 && (
            <p className="text-sm text-muted-foreground">Пока нет вызовов, заблокированных автоматически.</p>
          )}
          {data.recent.map((call) => (
            <CallListItem key={call.id} call={call} policy={policy} />
          ))}
        </div>
      </section>
    </div>
  );
}
