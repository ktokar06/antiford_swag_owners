import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, Globe, Printer } from 'lucide-react';
import { callsApi } from '@/api';
import { authApi } from '@/api/auth';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import ScoreBadge from '@/components/scoring/ScoreBadge';
import DecisionBadge from '@/components/scoring/DecisionBadge';
import ReviewBadge from '@/components/scoring/ReviewBadge';
import ModelExplanation from '@/components/scoring/ModelExplanation';
import useScoringConfig from '@/hooks/useScoringConfig';
import {
  maskNumber,
  formatDateTime,
  formatDuration,
  formatMoney,
  TIME_BUCKET_LABELS,
  CONNECTION_LABELS,
  DIRECTION_LABELS,
} from '@/libs/format';

const Row = ({ label, value }) => (
  <div className="flex items-start justify-between gap-6 border-b border-border py-3 last:border-0">
    <span className="text-xs uppercase tracking-[0.1em] text-muted-foreground">{label}</span>
    <span className="text-right text-sm">{value}</span>
  </div>
);

export default function CallDetail() {
  const { id } = useParams();
  const { policy } = useScoringConfig();
  const [call, setCall] = useState(null);
  const [note, setNote] = useState('');
  const [assignee, setAssignee] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    callsApi.get(id).then((record) => {
      setCall(record);
      setNote(record.review_note || '');
      setAssignee(record.assigned_to || '');
    }).catch(e => setError(e.message));
  }, [id]);

  const patch = async (data) => {
    setSaving(true);
    setError('');
    try { setCall(await callsApi.update(call.id, data)); }
    catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const applyReview = async (status) => {
    const user = await authApi.me();
    await patch({
      review_status: status,
      reviewed_by: user?.email,
      reviewed_at: new Date().toISOString(),
      review_note: note,
    });
  };

  if (!call && error) return <p role="alert">{error}</p>;
  if (!call) {
    return <div className="h-72 animate-pulse rounded-3xl bg-muted" />;
  }

  const score = call.risk_score;

  return (
    <div className="space-y-8">
      {error && <p role="alert" className="text-destructive">{error}</p>}
      <Link to="/calls" className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" /> К списку вызовов
      </Link>

      <header className="space-y-4">
        <div className="flex flex-wrap items-center gap-3 font-mono text-lg sm:text-xl">
          <span>{maskNumber(call.caller)}</span>
          <span className="text-muted-foreground">→</span>
          <span>{maskNumber(call.callee)}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span>{formatDateTime(call.started_at)}</span>
          <span>· длительность {formatDuration(call.duration_sec)}</span>
          {call.foreign_origin && (
            <span className="inline-flex items-center gap-1 text-risk-medium">
              <Globe className="h-3.5 w-3.5" /> вход из-за рубежа
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <DecisionBadge decision={call.decision} />
            <ReviewBadge status={call.review_status} />
          </div>
          <Button variant="outline" asChild>
            <Link to={`/calls/${call.id}/protocol`}>
              <Printer className="h-4 w-4" /> Протокол разбора
            </Link>
          </Button>
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="space-y-6 lg:col-span-3">
          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-lg font-semibold">Метаданные вызова</h2>
            <div className="mt-4">
              <Row label="Направление" value={DIRECTION_LABELS[call.direction]} />
              <Row label="Тип соединения" value={CONNECTION_LABELS[call.connection_type]} />
              <Row label="Время суток" value={TIME_BUCKET_LABELS[call.time_bucket]} />
              <Row label="Длительность" value={formatDuration(call.duration_sec)} />
              <Row label="Отбой на первой секунде" value={call.hung_up_first_second ? 'да' : 'нет'} />
              <Row label="Страна источника" value={call.source_country} />
              <Row label="Оператор источника" value={call.source_operator} />
              <Row label="Анализируемый номер" value={maskNumber(call.number_label)} />
              <Row label="Вторая сторона" value={maskNumber(call.counterpart)} />
              <Row
                label="Пригодность данных"
                value={call.is_valid ? 'валидные' : `невалидные — ${call.invalid_reason || 'причина не указана'}`}
              />
            </div>
            {call.number_ref && (
              <Link to={`/numbers/${call.number_ref}`} className="mt-4 inline-block text-xs text-primary">
                Открыть профиль номера →
              </Link>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-card p-6">
            <h2 className="font-display text-lg font-semibold">Разбор оператором</h2>
            <p className="mt-1 text-xs text-muted-foreground">
              {call.reviewed_by
                ? `Последнее решение: ${call.reviewed_by}, ${formatDateTime(call.reviewed_at)}`
                : 'Разбор ещё не проводился.'}
            </p>
            <Textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Комментарий для протокола разбора"
              className="mt-4 min-h-[90px] rounded-xl"
            />
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="outline" disabled={saving} onClick={() => applyReview('confirmed_fraud')}>
                Подтвердить мошенничество
              </Button>
              <Button variant="outline" disabled={saving} onClick={() => applyReview('false_positive')}>
                Ложное срабатывание
              </Button>
              <Button variant="outline" disabled={saving} onClick={() => applyReview('cleared')}>
                Проверено, чисто
              </Button>
            </div>
            <div className="mt-5 border-t border-border pt-4">
              <p className="text-xs uppercase tracking-[0.1em] text-muted-foreground">Ответственный оператор</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <input
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  placeholder="email оператора"
                  className="h-10 flex-1 rounded-xl border border-input bg-background px-3 text-sm outline-none focus:border-primary/50"
                />
                <Button variant="outline" disabled={saving || !assignee} onClick={() => patch({ assigned_to: assignee })}>
                  Назначить
                </Button>
              </div>
              {call.assigned_to && (
                <p className="mt-2 text-xs text-muted-foreground">Назначено: {call.assigned_to}</p>
              )}
            </div>
          </div>
        </section>

        <section className="space-y-4 lg:col-span-2">
          <div className="rounded-2xl border border-border bg-card p-6">
            <div className="flex items-center justify-between gap-4">
              <h2 className="font-display text-lg font-semibold">Итоговый скоринг</h2>
              <ScoreBadge score={score} policy={policy} />
            </div>
            <div className="mt-6">
              <ModelExplanation call={call} />
            </div>
          </div>

          {call.decision === 'auto_blocked' && (
            <div className="rounded-2xl border border-risk-high/30 bg-risk-high/5 p-6">
              <h3 className="font-display text-base font-semibold text-risk-high">Автоблокировка сработала</h3>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                Это отдельное решение: балл достиг порога {policy.auto_block_threshold}. Цена ошибки здесь
                зафиксирована политикой — ложная блокировка {formatMoney(policy.false_block_cost)}, пропущенное
                мошенничество {formatMoney(policy.missed_fraud_cost)}.
              </p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
