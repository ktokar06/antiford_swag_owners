export const DEFAULT_POLICY = {
  name: 'Базовая политика', review_threshold: 40, auto_block_threshold: 70,
  auto_block_enabled: true, false_block_cost: 1500, missed_fraud_cost: 12000,
};

export const DECISION_META = {
  unscored: { label: 'Ожидает ML-оценки', badge: 'border-border text-muted-foreground', dot: 'bg-muted' },
  allow: { label: 'Пропущен', badge: 'border-risk-low/30 bg-risk-low/10 text-risk-low', dot: 'bg-risk-low' },
  review: { label: 'На проверку', badge: 'border-risk-medium/30 bg-risk-medium/10 text-risk-medium', dot: 'bg-risk-medium' },
  auto_blocked: { label: 'Автоблокировка', badge: 'border-risk-high/30 bg-risk-high/10 text-risk-high', dot: 'bg-risk-high' },
};

export const REVIEW_META = {
  pending: { label: 'Ожидает разбора', badge: 'border-border bg-muted text-muted-foreground' },
  confirmed_fraud: { label: 'Мошенничество подтверждено', badge: 'border-risk-high/30 bg-risk-high/10 text-risk-high' },
  false_positive: { label: 'Ложное срабатывание', badge: 'border-risk-medium/30 bg-risk-medium/10 text-risk-medium' },
  cleared: { label: 'Проверено, чисто', badge: 'border-risk-low/30 bg-risk-low/10 text-risk-low' },
};

export const riskLevelFromScore = (score, policy = DEFAULT_POLICY) => {
  if (score >= Number(policy?.auto_block_threshold ?? DEFAULT_POLICY.auto_block_threshold)) return 'high';
  if (score >= Number(policy?.review_threshold ?? DEFAULT_POLICY.review_threshold)) return 'medium';
  return 'low';
};
