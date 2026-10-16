import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Search } from 'lucide-react';
import { callsApi } from '@/api';
import { Button } from '@/components/ui/button';
import CallListItem from '@/components/calls/CallListItem';
import useScoringConfig from '@/hooks/useScoringConfig';
import { formatNumber } from '@/libs/format';
import { cn } from '@/libs/utils';

const DECISION_OPTIONS = [
  { value: 'all', label: 'Все' },
  { value: 'auto_blocked', label: 'Автоблокировка' },
  { value: 'review', label: 'На проверку' },
  { value: 'allow', label: 'Пропущенные' },
];

const DIRECTION_OPTIONS = [
  { value: 'all', label: 'Все направления' },
  { value: 'incoming', label: 'Входящие' },
  { value: 'outgoing', label: 'Исходящие' },
  { value: 'forwarded', label: 'Переадресованные' },
];

const VALIDITY_OPTIONS = [
  { value: 'all', label: 'Любые данные' },
  { value: 'valid', label: 'Валидные' },
  { value: 'invalid', label: 'Невалидные' },
];

const pill = (active) =>
  cn(
    'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
    active
      ? 'border-primary/40 bg-accent text-accent-foreground'
      : 'border-border text-muted-foreground hover:text-foreground'
  );

export default function Calls() {
  const { policy } = useScoringConfig();
  const [decision, setDecision] = useState('all');
  const [direction, setDirection] = useState('all');
  const [validity, setValidity] = useState('all');
  const [foreignOnly, setForeignOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const requestId = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const buildQuery = useCallback(() => {
    const q = {};
    if (decision !== 'all') q.decision = decision;
    if (direction !== 'all') q.direction = direction;
    if (validity === 'valid') q.is_valid = true;
    if (validity === 'invalid') q.is_valid = false;
    if (foreignOnly) q.foreign_origin = true;
    const digits = debounced.replace(/\D/g, '');
    if (digits.length >= 3) q.search = digits;
    return q;
  }, [decision, direction, validity, foreignOnly, debounced]);

  useEffect(() => {
    const id = requestId.current + 1;
    requestId.current = id;
    setLoading(true);
    const query = buildQuery();
    Promise.all([
      callsApi.list({ ...query, sort: '-risk_score', limit: 50 }),
      callsApi.count(query),
    ]).then(([page, count]) => {
      if (requestId.current !== id) return;
      setItems(page.items || []);
      setCursor(page.next_cursor || null);
      setHasMore(Boolean(page.has_more));
      setTotal(count);
      setLoading(false);
    }).catch(() => {
      setItems([]);
      setTotal(0);
      setHasMore(false);
      setLoading(false);
    });
  }, [buildQuery]);

  const loadMore = async () => {
    const page = await callsApi.list({ ...buildQuery(), sort: '-risk_score', limit: 50, cursor });
    setItems((prev) => [...prev, ...(page.items || [])]);
    setCursor(page.next_cursor || null);
    setHasMore(Boolean(page.has_more));
  };

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Вызовы</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Разбор по метаданным</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {loading ? 'Загружаю выборку…' : `Найдено ${formatNumber(total)} записей. Отсортировано по убыванию балла риска.`}
        </p>
      </header>

      <div className="space-y-4 rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap gap-2">
          {DECISION_OPTIONS.map((o) => (
            <button key={o.value} onClick={() => setDecision(o.value)} className={pill(decision === o.value)}>
              {o.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {DIRECTION_OPTIONS.map((o) => (
            <button key={o.value} onClick={() => setDirection(o.value)} className={pill(direction === o.value)}>
              {o.label}
            </button>
          ))}
          {VALIDITY_OPTIONS.map((o) => (
            <button key={o.value} onClick={() => setValidity(o.value)} className={pill(validity === o.value)}>
              {o.label}
            </button>
          ))}
          <button onClick={() => setForeignOnly((v) => !v)} className={pill(foreignOnly)}>
            Только из-за рубежа
          </button>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по номеру вызывающего или вызываемого"
            className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 font-mono text-sm outline-none transition-colors placeholder:font-body placeholder:text-muted-foreground focus:border-primary/50"
          />
        </div>
      </div>

      <div className="space-y-3">
        {!loading && items.length === 0 && (
          <p className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Под эти условия записей нет. Смягчите фильтры.
          </p>
        )}
        {items.map((call) => (
          <CallListItem key={call.id} call={call} policy={policy} />
        ))}
      </div>

      {hasMore && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadMore}>
            Показать ещё 50
          </Button>
        </div>
      )}
    </div>
  );
}