import { format } from 'date-fns';
import { ru } from 'date-fns/locale';

export const maskNumber = (value) => {
  if (!value) return '—';
  const digits = String(value).replace(/\D/g, '');
  if (digits.length < 7) return String(value);
  const country = digits.slice(0, 1);
  const code = digits.slice(1, 4);
  const tail = digits.slice(-2);
  return `+${country} ${code} •••-••-${tail}`;
};

export const formatNumber = (value) => new Intl.NumberFormat('ru-RU').format(Number(value) || 0);

export const formatPercent = (value) => `${Math.round((Number(value) || 0) * 100)}%`;

export const formatMoney = (value) => `${formatNumber(Math.round(Number(value) || 0))} ₽`;

export const formatDuration = (sec) => {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  if (s < 60) return `${s} сек`;
  return `${Math.floor(s / 60)} мин ${s % 60} сек`;
};

export const formatDateTime = (value) =>
  value ? format(new Date(value), 'd MMM yyyy, HH:mm', { locale: ru }) : '—';

export const formatDay = (value) => (value ? format(new Date(value), 'd MMM', { locale: ru }) : '—');

export const formatShortDate = (value) => (value ? format(new Date(value), 'd MMM yyyy', { locale: ru }) : '—');

export const formatPeriod = (from, to) =>
  from && to ? `${formatShortDate(from)} — ${formatShortDate(to)}` : '—';

export const TIME_BUCKET_LABELS = {
  night: 'ночь, 00:00–06:00',
  morning: 'утро, 06:00–12:00',
  day: 'день, 12:00–18:00',
  evening: 'вечер, 18:00–24:00',
};

export const CONNECTION_LABELS = {
  mobile: 'Мобильная сеть',
  pstn: 'Фиксированная сеть',
  voip: 'VoIP',
  sip_gateway: 'SIP-шлюз',
  roaming: 'Роуминг',
};

export const DIRECTION_LABELS = {
  incoming: 'Входящий',
  outgoing: 'Исходящий',
  forwarded: 'Переадресованный',
};

export const KIND_LABELS = {
  mobile: 'Мобильный',
  landline: 'Городской',
  virtual: 'Виртуальный',
  unknown: 'Не определён',
};