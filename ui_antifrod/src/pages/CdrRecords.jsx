import React, { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, Search, Upload, FolderInput } from 'lucide-react';
import { cdrApi, statsApi } from '@/api';
import { Button } from '@/components/ui/button';
import { formatDateTime, formatNumber, DIRECTION_LABELS } from '@/libs/format';
import { cn } from '@/libs/utils';

const PAGE_SIZE = 50;

const TABS = [
  { key: 'files', label: 'Файлы' },
  { key: 'valid', label: 'Валидные записи' },
  { key: 'invalid', label: 'Невалидные записи' },
];

const STATUS_LABELS = {
  loaded: 'загружен',
  skipped_duplicate: 'дубликат файла',
  conflict: 'конфликт имени',
};

const pill = (active) =>
  cn(
    'rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
    active ? 'border-primary/40 bg-accent text-accent-foreground' : 'border-border text-muted-foreground hover:text-foreground'
  );

function Pager({ offset, total, onChange }) {
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const current = Math.floor(offset / PAGE_SIZE) + 1;
  return (
    <nav className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted-foreground" aria-label="Пагинация">
      <span>
        {total === 0
          ? 'Записей нет'
          : `${formatNumber(offset + 1)}–${formatNumber(Math.min(offset + PAGE_SIZE, total))} из ${formatNumber(total)}`}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" disabled={current <= 1} onClick={() => onChange(offset - PAGE_SIZE)}>
          Назад
        </Button>
        <span className="font-mono tabular-nums">
          {current} / {pages}
        </span>
        <Button variant="outline" size="sm" disabled={current >= pages} onClick={() => onChange(offset + PAGE_SIZE)}>
          Вперёд
        </Button>
      </div>
    </nav>
  );
}

function Th({ children, right }) {
  return <th className={cn('px-3 py-2.5 font-medium', right && 'text-right')}>{children}</th>;
}

function Td({ children, right, mono, className }) {
  return (
    <td className={cn('px-3 py-2.5 align-top', right && 'text-right', mono && 'font-mono tabular-nums', className)}>
      {children}
    </td>
  );
}

export default function CdrRecords() {
  const [params, setParams] = useSearchParams();
  const tab = params.get('tab') || 'files';
  const fileId = params.get('cdr_file_id') || '';
  const errorCode = params.get('error_code') || '';
  const type = params.get('type') || '';

  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reasons, setReasons] = useState([]);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const fileInput = useRef(null);
  const requestId = useRef(0);

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search.trim()), 300);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => setOffset(0), [tab, fileId, errorCode, type, debounced]);

  useEffect(() => {
    statsApi.invalidReasons().then((r) => setReasons(r.rows || [])).catch(() => setReasons([]));
  }, [reload]);

  useEffect(() => {
    const id = requestId.current + 1;
    requestId.current = id;
    setLoading(true);
    setError('');
    const query = { limit: PAGE_SIZE, offset, search: debounced };
    const request =
      tab === 'files'
        ? cdrApi.files(query)
        : tab === 'valid'
          ? cdrApi.valid({ ...query, cdr_file_id: fileId, type })
          : cdrApi.invalid({ ...query, cdr_file_id: fileId, error_code: errorCode });
    request
      .then((page) => {
        if (requestId.current === id) setData(page);
      })
      .catch((e) => {
        if (requestId.current === id) setError(e.message || 'Не удалось загрузить записи');
      })
      .finally(() => {
        if (requestId.current === id) setLoading(false);
      });
  }, [tab, fileId, errorCode, type, debounced, offset, reload]);

  const waitForJob = async () => {
    for (let i = 0; i < 900; i += 1) {
      const job = await cdrApi.job();
      if (!job.running) return job;
      setNotice(`Идёт обработка: ${job.stage || 'очередь'}…`);
      await new Promise((r) => setTimeout(r, 2000));
    }
    return null;
  };

  const onUpload = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (!files.length) return;
    setBusy(true);
    setNotice('');
    const lines = [];
    for (const file of files) {
      try {
        const res = await cdrApi.upload(file);
        lines.push(
          res.status === 'loaded'
            ? `${file.name}: валидных ${formatNumber(res.rows_valid)}, дубликатов ${formatNumber(res.rows_duplicate)}, невалидных ${formatNumber(res.rows_invalid)}`
            : `${file.name}: ${res.message}`
        );
      } catch (e) {
        lines.push(`${file.name}: ошибка — ${e.message}`);
      }
    }
    const job = await waitForJob();
    lines.push(job?.error ? `Пересчёт: ошибка — ${job.error}` : 'Скоринг и статистика пересчитаны.');
    setNotice(lines.join('\n'));
    setBusy(false);
    setReload((n) => n + 1);
  };

  const onImport = async () => {
    setBusy(true);
    setNotice('');
    try {
      await cdrApi.importDirectory();
      const job = await waitForJob();
      const load = job?.result?.load;
      setNotice(
        job?.error
          ? `Импорт завершился с ошибкой: ${job.error}`
          : load
            ? `Файлов: ${formatNumber(load.files)} (новых ${formatNumber(load.loaded)}, уже загруженных ${formatNumber(load.skipped)}, конфликтов ${formatNumber(load.conflicts)}). ` +
              `Валидных ${formatNumber(load.rows_valid)}, дубликатов ${formatNumber(load.rows_duplicate)}, невалидных ${formatNumber(load.rows_invalid)}.`
            : 'Импорт завершён.'
      );
    } catch (e) {
      setNotice(e.message || 'Не удалось запустить импорт');
    } finally {
      setBusy(false);
      setReload((n) => n + 1);
    }
  };

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">CDR_OUT</p>
        <h1 className="font-display text-3xl font-semibold tracking-tight sm:text-4xl">Записи CDR</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Исходные файлы, принятые записи и строки, не прошедшие валидацию, с причиной отказа. Повторная загрузка того же
          файла или тех же строк дубликатов не создаёт.
        </p>
      </header>

        <section className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card p-5">
          <input ref={fileInput} type="file" accept=".cdr,.csv" multiple className="hidden" onChange={onUpload} />
          <Button onClick={() => fileInput.current?.click()} disabled={busy}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
            Загрузить .cdr / .csv
          </Button>
          <Button variant="outline" onClick={onImport} disabled={busy}>
            <FolderInput className="h-4 w-4" />
            Импортировать каталог CDR_OUT
          </Button>
          {notice && <p className="w-full whitespace-pre-line text-sm text-primary">{notice}</p>}
        </section>

      <div className="space-y-4 rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap gap-2" role="tablist">
          {TABS.map((t) => (
            <button key={t.key} role="tab" aria-selected={tab === t.key} onClick={() => setParam('tab', t.key)} className={pill(tab === t.key)}>
              {t.label}
            </button>
          ))}
          {fileId && (
            <button onClick={() => setParam('cdr_file_id', '')} className={pill(true)}>
              файл #{fileId} ✕
            </button>
          )}
        </div>

        {tab === 'valid' && (
          <div className="flex flex-wrap gap-2">
            {['', '01', '02', '03'].map((t) => (
              <button key={t || 'all'} onClick={() => setParam('type', t)} className={pill(type === t)}>
                {t ? `Тип ${t}` : 'Все типы'}
              </button>
            ))}
          </div>
        )}

        {tab === 'invalid' && (
          <div className="flex flex-wrap gap-2">
            <button onClick={() => setParam('error_code', '')} className={pill(!errorCode)}>
              Все причины
            </button>
            {reasons.map((r) => (
              <button key={r.code} onClick={() => setParam('error_code', r.code)} className={pill(errorCode === r.code)}>
                {r.label} · {formatNumber(r.count)}
              </button>
            ))}
          </div>
        )}

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Поиск"
            placeholder={
              tab === 'files' ? 'Имя файла' : tab === 'valid' ? 'Цифры номера A, B или IMSI' : 'Фрагмент исходной строки'
            }
            className="h-10 w-full rounded-xl border border-input bg-background pl-9 pr-3 font-mono text-sm outline-none placeholder:font-body placeholder:text-muted-foreground focus:border-primary/50"
          />
        </div>
      </div>

      {error && <p className="text-sm text-risk-high">{error}</p>}

      <div className={cn('overflow-x-auto rounded-2xl border border-border bg-card transition-opacity', loading && 'opacity-60')}>
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] uppercase tracking-[0.1em] text-muted-foreground">
            {tab === 'files' && (
              <tr className="border-b border-border">
                <Th>Файл</Th><Th>Статус</Th><Th>Загружен</Th><Th right>Строк</Th><Th right>Валидных</Th><Th right>Дубликатов</Th><Th right>Невалидных</Th>
              </tr>
            )}
            {tab === 'valid' && (
              <tr className="border-b border-border">
                <Th>Файл / строка</Th><Th>Тип</Th><Th>Номер A</Th><Th>Номер B</Th><Th>Номер C</Th><Th>Начало</Th><Th right>Длит., сек</Th><Th>IMSI</Th>
              </tr>
            )}
            {tab === 'invalid' && (
              <tr className="border-b border-border">
                <Th>Файл / строка</Th><Th>Причина</Th><Th>Исходная строка</Th>
              </tr>
            )}
          </thead>
          <tbody>
            {!loading && data.items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-3 py-6 text-muted-foreground">Под эти условия записей нет.</td>
              </tr>
            )}
            {tab === 'files' &&
              data.items.map((f) => (
                <tr key={f.id} className="border-b border-border last:border-0">
                  <Td mono>{f.filename}</Td>
                  <Td className="text-xs">{STATUS_LABELS[f.status] || f.status}</Td>
                  <Td className="text-xs text-muted-foreground">{formatDateTime(f.loaded_at)}</Td>
                  <Td right mono>{formatNumber(f.rows_total)}</Td>
                  <Td right mono>
                    <button className="hover:text-primary" onClick={() => setParams({ tab: 'valid', cdr_file_id: String(f.id) })}>
                      {formatNumber(f.rows_valid)}
                    </button>
                  </Td>
                  <Td right mono>{formatNumber(f.rows_duplicate)}</Td>
                  <Td right mono className={f.rows_invalid ? 'text-risk-high' : ''}>
                    <button className="hover:text-primary" onClick={() => setParams({ tab: 'invalid', cdr_file_id: String(f.id) })}>
                      {formatNumber(f.rows_invalid)}
                    </button>
                  </Td>
                </tr>
              ))}
            {tab === 'valid' &&
              data.items.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <Td className="text-xs text-muted-foreground">{r.filename || '—'} · {r.row_num ?? '—'}</Td>
                  <Td className="text-xs">{r.type} {DIRECTION_LABELS[r.direction] ? `· ${DIRECTION_LABELS[r.direction]}` : ''}</Td>
                  <Td mono>{r.num_a}</Td>
                  <Td mono>{r.num_b}</Td>
                  <Td mono>{r.num_c || '—'}</Td>
                  <Td className="text-xs">{formatDateTime(r.started_at)}</Td>
                  <Td right mono>{r.duration_sec}</Td>
                  <Td mono className="text-xs">{r.imsi || '—'}</Td>
                </tr>
              ))}
            {tab === 'invalid' &&
              data.items.map((r) => (
                <tr key={r.id} className="border-b border-border last:border-0">
                  <Td className="whitespace-nowrap text-xs text-muted-foreground">{r.filename || '—'} · {r.row_num ?? '—'}</Td>
                  <Td className="text-xs text-risk-high">{r.reason}</Td>
                  <Td mono className="max-w-xl break-all text-xs">{r.raw_line}</Td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <Pager offset={offset} total={data.total || 0} onChange={(o) => setOffset(Math.max(0, o))} />
    </div>
  );
}
