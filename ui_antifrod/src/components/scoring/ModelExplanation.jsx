import React from 'react';

export default function ModelExplanation({ call }) {
  const explanation = call.explanation;
  return <div className="space-y-4">
    <p className="text-sm">CatBoost · риск <strong>{call.risk_score}/100</strong>
      {call.probability != null && ` · вероятность ${(call.probability * 100).toFixed(2)}%`}</p>
    <p className="break-all font-mono text-xs text-muted-foreground">Модель: {call.model_version || 'оценка ещё не выполнена'}</p>
    {explanation ? <>
      <p className="text-xs text-muted-foreground">SHAP: положительный вклад повышает риск, отрицательный снижает. Единица — log-odds. База {explanation.base_log_odds.toFixed(4)}; sigmoid(база + сумма вкладов) = вероятность.</p>
      <div className="space-y-3">{explanation.factors.map(f => <div key={f.feature} className="flex justify-between gap-4 border-b border-border pb-2 text-sm">
        <div><p>{f.label || f.feature}</p><p className="text-xs text-muted-foreground">Значение: {typeof f.value === 'number' ? Number(f.value.toFixed(4)) : String(f.value ?? '')}</p></div>
        <span className={`font-mono ${f.contribution > 0 ? 'text-risk-high' : 'text-risk-low'}`}>{f.contribution > 0 ? '+' : ''}{f.contribution.toFixed(4)}</span>
      </div>)}</div>
    </> : <p className="text-sm text-muted-foreground">Объяснение отсутствует: выполните пересчёт действующей моделью.</p>}
  </div>;
}
