import React, { useEffect, useState } from 'react';
import { rulesApi, cdrApi } from '@/api';
import { apiFetch } from '@/api/client';
import useScoringConfig from '@/hooks/useScoringConfig';
import { Button } from '@/components/ui/button';

export default function Rules() {
  const { policy, reload } = useScoringConfig();
  const [draft, setDraft] = useState(policy);
  const [model, setModel] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { setDraft(policy); }, [policy]);
  useEffect(() => { apiFetch('/api/ml/model').then(setModel).catch(e => setMessage(e.message)); }, []);
  async function save() {
    setBusy(true);
    try { await rulesApi.updatePolicy(draft); await reload(); setMessage('Политика сохранена. Пересчитайте решения.'); }
    catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  async function rescore() {
    setBusy(true);
    try {
      await rulesApi.rescore();
      setMessage('Выполняется прогноз CatBoost…');
      for (let i = 0; i < 1800; i++) {
        await new Promise(resolve => setTimeout(resolve, 2000));
        const job = await cdrApi.job();
        setMessage(`Обработка: ${job.stage || 'завершение'}`);
        if (!job.running) { setMessage(job.error || `Готово: ${job.result?.scoring?.scored_calls ?? 0} предсказаний.`); return; }
      }
      setMessage('Задача продолжается. Статус доступен на странице CDR.');
    } catch (e) { setMessage(e.message); } finally { setBusy(false); }
  }
  return <div className="space-y-6">
    <h1 className="text-3xl font-semibold">Модель и политика решений</h1>
    <p className="text-muted-foreground">Риск рассчитывает обученный CatBoost. Пороги определяют отправку оператору и автоблокировку.</p>
    <section className="rounded-2xl border border-border p-6 space-y-3">
      <h2 className="text-xl">Обученная модель</h2>
      {model ? <><p>CatBoost · {model.features.length} признаков · версия {model.model_sha256.slice(0, 12)}</p>
        <p>Обучена: {new Date(model.created_at).toLocaleString('ru-RU')}</p>
        <p>Test при пороге {model.metrics?.test?.threshold}: ROC-AUC {model.metrics?.test?.roc_auc?.toFixed(3)}, recall {((model.metrics?.test?.recall ?? 0)*100).toFixed(2)}%, FPR {((model.metrics?.test?.false_positive_rate ?? 0)*100).toFixed(2)}%</p>
        <p className="text-xs text-muted-foreground">Метрики относительно разметки сценариев хакатона. Веса признаков выучены при обучении.</p>
      </> : <p>Загрузка модели…</p>}
    </section>
    <section className="rounded-2xl border border-border p-6 space-y-4">
      <h2 className="text-xl">Пороги действий</h2>
      <div className="grid gap-4 sm:grid-cols-2">{[
        ['review_threshold', 'Порог проверки'], ['auto_block_threshold', 'Порог автоблокировки'],
        ['false_block_cost', 'Цена ложной блокировки'], ['missed_fraud_cost', 'Цена пропуска фрода'],
      ].map(([key, label]) => <label key={key} className="space-y-2"><span className="block text-sm">{label}</span>
        <input type="number" min="0" value={draft[key] ?? 0} onChange={e => setDraft({...draft, [key]: Number(e.target.value)})} className="w-full rounded border border-input bg-background p-2" />
      </label>)}</div>
      <label className="flex gap-2"><input type="checkbox" checked={draft.auto_block_enabled !== false} onChange={e => setDraft({...draft, auto_block_enabled: e.target.checked})}/>Автоблокировка</label>
      <div className="flex gap-3"><Button disabled={busy} onClick={save}>Сохранить политику</Button><Button disabled={busy} variant="outline" onClick={rescore}>Пересчитать моделью</Button></div>
    </section>
    {message && <p role="status">{message}</p>}
  </div>;
}
