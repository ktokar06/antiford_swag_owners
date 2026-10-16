export function safeReturnTo(fallback = '/') {
  if (typeof window === 'undefined') return fallback;
  const params = new URLSearchParams(window.location.search);
  const returnTo = params.get('returnTo');
  if (!returnTo) return fallback;
  if (!returnTo.startsWith('/') || returnTo.startsWith('//')) return fallback;
  return returnTo;
}