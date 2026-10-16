import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { callsApi } from '@/api';
import { Button } from '@/components/ui/button';
import ModelExplanation from '@/components/scoring/ModelExplanation';
import { formatDateTime, maskNumber } from '@/libs/format';
import { DECISION_META, REVIEW_META } from '@/libs/scoring';

export default function CallProtocol() {
  const { id } = useParams();
  const [call, setCall] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { callsApi.get(id).then(setCall).catch(e => setError(e.message)); }, [id]);
  if (error) return <p>{error}</p>;
  if (!call) return <p>Загрузка протокола…</p>;
  return <article className="mx-auto max-w-3xl space-y-6 p-6">
    <div className="flex justify-between print:hidden"><Link to={`/calls/${id}`}>← Карточка вызова</Link><Button onClick={() => window.print()}>Печать / PDF</Button></div>
    <h1 className="text-2xl font-semibold">Протокол ML-анализа вызова №{id}</h1>
    <p>{maskNumber(call.caller)} → {maskNumber(call.callee)} · {formatDateTime(call.started_at)} · {call.duration_sec} с</p>
    <p>Решение: {DECISION_META[call.decision]?.label || call.decision}</p>
    <ModelExplanation call={call}/>
    <section className="border-t border-border pt-4"><h2 className="text-xl">Разбор оператором</h2>
      <p>{REVIEW_META[call.review_status]?.label}</p><p>{call.reviewed_by || 'Не разобран'} · {call.review_note || 'Комментария нет'}</p>
    </section>
    <p className="text-xs text-muted-foreground">Вероятность получена обученной моделью по метаданным CDR. SHAP объясняет вклад признаков; содержание разговора не используется.</p>
  </article>;
}
