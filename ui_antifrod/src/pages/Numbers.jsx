import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { numbersApi } from '@/api';
import { Button } from '@/components/ui/button';
import NumberListItem from '@/components/numbers/NumberListItem';
import { formatNumber } from '@/libs/format';
import { cn } from '@/libs/utils';

const VALIDITY_OPTIONS = [
  { value: 'all', label: 'Любая база' },
  { value: 'valid', label: 'Валидные' },
  { value: 'invalid', label: 'Невалидные данные' },
];

const DIRECTION_OPTIONS = [
  { value: 'all', label: 'Все направления' },
  { value: 'incoming', label: 'С входящими' },
  { value: 'outgoing', label: 'С исходящими' },
  { value: 'forwarded', label: 'С переадресацией' },
];

const pill = (active) =>
  cn(
    'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
    active
      ? 'border-primary/40 bg-accent text-accent-foreground'
      : 'border-border text-muted-foreground hover:text-foreground'
  );

export default function Numbers() {
  const [validity, setValidity] = useState('all');
  const [direction, setDirection] = useState('all');
  const [fanOnly, setFanOnly] = useState(false);
  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [cursor, setCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  const buildQuery = useCallback(() => {
    const q = {};
    if (validity === 'valid') q.is_valid = true;
    if (validity === 'invalid') q.is_valid = false;
    if (direction === 'incoming') q.has_incoming = true;
    if (direction === 'outgoing') q.has_outgoing = true;
    if (direction === 'forwarded') q.has_forwarded = true;
    if (fanOnly) q.has_fan_pattern = true;
    const text = debounced.trim();
    if (text) {
      const digits = text.replace(/\D/g, '');
      q.search_text = text;
      if (digits.length >= 3) q.search_digits = digits;
    }
    return q;
  }, [validity, direction, fanOnly, debounced]);

  useEffect(() => {
    setLoading(true);
    const query = buildQuery();
    Promise.all([
      numbersApi.list({ ...query, sort: '-max_risk_score', limit: 50 }),
      numbersApi.count(query),
    ]).then(([page, count]) => {
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
    const page = await numbersApi.list({ ...buildQuery(), sort: '-max_risk_score', limit: 50, cursor });
    setItems((prev) => [...prev, ...(page.items || [])]);
    setCursor(page.next_cursor || null);
    setHasMore(Boolean(page.has_more));
  };

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">Номера</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">База номеров</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          {loading ? 'Загружаю базу…' : `${formatNumber(total)} номеров под условия отбора.`}
        </p>
      </header>

      <div className="space-y-4 rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap gap-2">
          {VALIDITY_OPTIONS.map((o) => (
            <button key={o.value} onClick={() => setValidity(o.value)} className={pill(validity === o.value)}>
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
          <button onClick={() => setFanOnly((v) => !v)} className={pill(fanOnly)}>
            Только веера
          </button>
        </div>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Абонент, регион или цифры номера"
            className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 text-sm outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50"
          />
        </div>
      </div>

      <div className="space-y-3">
        {!loading && items.length === 0 && (
          <p className="rounded-2xl border border-border bg-card p-6 text-sm text-muted-foreground">
            Под эти условия номеров нет.
          </p>
        )}
        {items.map((record) => (
          <NumberListItem key={record.id} record={record} />
        ))}
      </div>

      {hasMore && (
        <div className="flex justify-center">
          <Button variant="outline" onClick={loadMore}>
            Показать ещё 50
          </Button>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        Номера показаны в маскированном виде.{' '}
        <Link to="/" className="text-primary">
          Вернуться к обзору базы →
        </Link>
      </p>
    </div>
  );
}