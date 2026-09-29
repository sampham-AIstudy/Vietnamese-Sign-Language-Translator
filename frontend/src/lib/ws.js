/**
 * WebSocket URL + client clock shared by the two live modes (plan 06 §3.4).
 *
 * Every WebSocket of the app goes through the page's own origin: the Vite dev/preview server proxies /ws to the
 * backend (frontend/vite.config.js), so no backend host/port is written anywhere in frontend/src.
 */

/** `ws(s)://<page host>/<path>` — wss when the page is served over https; the host keeps its port. */
export function wsUrl(location, path) {
  const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
  const p = path.startsWith('/') ? path : `/${path}`;
  return `${scheme}://${location.host}${p}`;
}

/**
 * Client timestamp in ms: performance.timeOrigin + performance.now() — monotonic within a page (never goes back
 * when the system clock is adjusted, unlike Date.now()), so the server's timestamp checks do not fail.
 */
export function nowMs() {
  return performance.timeOrigin + performance.now();
}
