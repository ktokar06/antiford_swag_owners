import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Ban, Network, Search, SlidersHorizontal } from 'lucide-react';
import { callsApi, blocksApi } from '@/api';
import { Button } from '@/components/ui/button';
import ScoreBadge from '@/components/scoring/ScoreBadge';
import ReviewBadge from '@/components/scoring/ReviewBadge';
import StatCard from '@/components/stats/StatCard';
import useScoringConfig from '@/hooks/useScoringConfig';
import { formatDateTime, formatMoney, formatNumber, maskNumber } from '@/libs/format';

export default function Blocks() {
  const { policy } = useScoringConfig();
  const [counts, setCounts] = useState(null);
  const [journal, setJournal] = useState([]);
  const [journalCursor, setJournalCursor] = useState(null);
  const [numbers, setNumbers] = useState({ items: [], total: 0, has_more: false, next_cursor: null });
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.replace(/\D/g, '')), 300);
    return () => clearTimeout(t);
  }, [search]);

  const load = useCallback(async () => {
    try {
      const [summary, page] = await Promise.all([
        blocksApi.summary(),
        blocksApi.journal({ sort: '-started_at', limit: 50 }),
      ]);
      setCounts(summary);
      setJournal(page.items || []);
      setJournalCursor(page.has_more ? page.next_cursor : null);
    } catch (e) {
      setError(e.message || 'Не удалось загрузить журнал');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    blocksApi
      .numbers({ search: debounced, limit: 20 })
      .then(setNumbers)
      .catch((e) => setError(e.message || 'Не удалось загрузить номера'));
  }, [debounced]);

  const moreNumbers = async () => {
    const page = await blocksApi.numbers({ search: debounced, limit: 20, cursor: numbers.next_cursor });
    setNumbers((prev) => ({ ...page, items: [...prev.items, ...page.items] }));
  };

  const moreJournal = async () => {
    const page = await blocksApi.journal({ sort: '-started_at', limit: 50, cursor: journalCursor });
    setJournal((prev) => [...prev, ...(page.items || [])]);
    setJournalCursor(page.has_more ? page.next_cursor : null);
  };

  const mark = async (call, review_status) => {
    await callsApi.update(call.id, { review_status });
    await load();
  };

  const falsePositiveCost = (counts?.falsePositive || 0) * Number(policy.false_block_cost || 0);
  const missedCost = (counts?.missed || 0) * Number(policy.missed_fraud_cost || 0);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Автоблокировка</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Отдельное решение</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Скоринг выставляет балл, автоблокировка принимает решение по своему порогу. Ошибка здесь стоит денег
          в обе стороны — и когда блокируем обычного человека, и когда пропускаем мошенника.
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Заблокировано" value={formatNumber(counts?.blocked ?? 0)} hint="вызовов закрыто автоматически" icon={Ban} tone="high" />
        <StatCard label="Подтверждено" value={formatNumber(counts?.confirmed ?? 0)} hint="оператор подтвердил мошенничество" tone="low" />
        <StatCard label="Ложных блокировок" value={formatNumber(counts?.falsePositive ?? 0)} hint="заблокирован обычный человек" tone="medium" />
        <StatCard label="Ожидают разбора" value={formatNumber(counts?.pending ?? 0)} hint="решение ещё не проверено" />
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-2xl border border-border bg-card p-6 lg:col-span-2">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-display text-lg font-semibold">Цена ошибки</h2>
            <Link to="/rules" className="inline-flex items-center gap-1 text-xs text-primary">
              <SlidersHorizontal className="h-3 w-3" /> Изменить пороги
            </Link>
          </div>
          <div className="mt-5 space-y-4">
            <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-border pb-3">
              <div>
                <p className="text-sm">Ложные блокировки</p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(counts?.falsePositive ?? 0)} × {formatMoney(policy.false_block_cost)}
                </p>
              </div>
              <span className="font-mono text-base tabular-nums text-risk-medium">{formatMoney(falsePositiveCost)}</span>
            </div>
            <div className="flex flex-wrap items-baseline justify-between gap-3 border-b border-border pb-3">
              <div>
                <p className="text-sm">Пропущенное мошенничество</p>
                <p className="text-xs text-muted-foreground">
                  {formatNumber(counts?.missed ?? 0)} × {formatMoney(policy.missed_fraud_cost)}
                </p>
              </div>
              <span className="font-mono text-base tabular-nums text-risk-high">{formatMoney(missedCost)}</span>
            </div>
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <p className="text-sm font-medium">Итого цена ошибки политики</p>
              <span className="font-display text-2xl font-semibold tabular-nums">{formatMoney(falsePositiveCost + missedCost)}</span>
            </div>
          </div>
        </div>

        <div className="rounded-2xl border border-border bg-card p-6">
          <h2 className="font-display text-lg font-semibold">Текущий порог</h2>
          <p className="mt-4 font-display text-4xl font-semibold tabular-nums">{policy.auto_block_threshold}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            балл, с которого вызов блокируется автоматически
          </p>
          <dl className="mt-5 space-y-2 border-t border-border pt-4 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Порог проверки</dt>
              <dd className="font-mono tabular-nums">{policy.review_threshold}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Автоблокировка</dt>
              <dd>{policy.auto_block_enabled === false ? 'выключена' : 'включена'}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Изменил</dt>
              <dd className="truncate">{policy.updated_by || 'политика по умолчанию'}</dd>
            </div>
          </dl>
        </div>
      </section>

      {error && <p className="text-sm text-risk-high">{error}</p>}

      <section className="space-y-4">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="font-display text-lg font-semibold">Заблокированные номера</h2>
          <p className="text-xs text-muted-foreground">
            {formatNumber(numbers.total)} номеров с автоблокировкой
          </p>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по цифрам номера"
            aria-label="Поиск заблокированного номера"
            className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 font-mono text-sm outline-none focus:border-primary/50"
          />
        </div>
        <div className="overflow-x-auto rounded-2xl border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="text-left text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
              <tr className="border-b border-border">
                <th className="px-4 py-3 font-medium">Номер</th>
                <th className="px-4 py-3 text-right font-medium">Блокировок</th>
                <th className="px-4 py-3 text-right font-medium">Макс. балл</th>
                <th className="px-4 py-3 font-medium">Последняя</th>
                <th className="px-4 py-3 text-right font-medium">Подтв. / ложн.</th>
              </tr>
            </thead>
            <tbody>
              {numbers.items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-muted-foreground">Заблокированных номеров нет.</td>
                </tr>
              )}
              {numbers.items.map((n) => (
                <tr key={n.number} className="border-b border-border last:border-0">
                  <td className="px-4 py-3 font-mono">
                    {n.number_ref ? (
                      <Link to={`/numbers/${n.number_ref}`} className="hover:text-primary">{maskNumber(n.number)}</Link>
                    ) : (
                      maskNumber(n.number)
                    )}
                    {n.has_fan_pattern && <Network className="ml-2 inline h-3 w-3 text-risk-high" aria-label="веер" />}
                  </td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{formatNumber(n.blocked_calls)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">{n.max_risk_score}</td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">{formatDateTime(n.last_blocked_at)}</td>
                  <td className="px-4 py-3 text-right font-mono tabular-nums">
                    {n.confirmed} / {n.false_positive}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {numbers.has_more && (
          <div className="flex justify-center">
            <Button variant="outline" onClick={moreNumbers}>Показать ещё</Button>
          </div>
        )}
      </section>

      <section className="space-y-4">
        <h2 className="font-display text-lg font-semibold">Журнал блокировок</h2>
        <div className="space-y-3">
          {journal.length === 0 && (
            <p className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
              Автоблокировка пока не срабатывала.
            </p>
          )}
          {journal.map((call) => (
            <div key={call.id} className="rounded-2xl border border-border bg-card p-4">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0 space-y-1.5">
                  <Link to={`/calls/${call.id}`} className="font-mono text-sm hover:text-primary">
                    {maskNumber(call.caller)} → {maskNumber(call.callee)}
                  </Link>
                  <p className="text-xs text-muted-foreground">
                    {formatDateTime(call.started_at)} · {call.source_country} · {maskNumber(call.number_label)}
                  </p>
                  <ReviewBadge status={call.review_status} />
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <ScoreBadge score={call.risk_score} policy={policy} />
                  <Button variant="outline" onClick={() => mark(call, 'confirmed_fraud')}>
                    Мошенник
                  </Button>
                  <Button variant="outline" onClick={() => mark(call, 'false_positive')}>
                    Ложная блокировка
                  </Button>
                </div>
              </div>
            </div>
          ))}
        </div>
        {journalCursor && (
          <div className="flex justify-center">
            <Button variant="outline" onClick={moreJournal}>Показать ещё 50</Button>
          </div>
        )}
      </section>
    </div>
  );
}