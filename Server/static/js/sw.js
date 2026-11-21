/* MediGen service worker.
   1. Static files (CSS, JS, icons) are cached so the app opens faster and can be installed.
   2. The sale page (/sales/new) is cached after each successful online visit, so it still opens when the
      network drops. The cached copy is used for at most 24 hours; after that it is refused.
   Every other page and every API response always comes from the server. */
const CACHE = 'medigen-static-v5';
const PAGE_CACHE = 'medigen-pages-v1';
const SALE_PATH = '/sales/new';
const PAGE_MAX_AGE_MS = 24 * 60 * 60 * 1000;
const CACHED_AT_HEADER = 'X-MediGen-Cached-At';
const ASSETS = [
  '/static/css/classic.css',
  '/static/css/pages.css',
  '/static/css/brand.css',
  '/static/css/theme.css',
  '/static/css/glow-card.css',
  '/static/js/glow-card.js',
  '/static/js/app.js',
  '/static/js/charts.js',
  '/static/js/scanner.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  const keep = [CACHE, PAGE_CACHE];
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !keep.includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function offlinePage(message) {
  const html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<title>Offline</title></head><body style="font-family:sans-serif;padding:24px;line-height:1.5">' +
    '<h2>Offline</h2><p>' + message + '</p></body></html>';
  return new Response(html, { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } });
}

// Network first. A successful online visit is stored with its time. When the network fails, the stored copy
// is used only if it is less than 24 hours old.
async function saleNetworkFirst(req) {
  const cache = await caches.open(PAGE_CACHE);
  try {
    const res = await fetch(req);
    const finalPath = new URL(res.url).pathname;
    if (res.ok && !res.redirected && finalPath === SALE_PATH && (res.headers.get('content-type') || '').includes('text/html')) {
      const body = await res.clone().blob();
      const headers = new Headers(res.headers);
      headers.set(CACHED_AT_HEADER, String(Date.now()));
      await cache.put(SALE_PATH, new Response(body, { status: 200, headers: headers }));
    }
    return res;
  } catch (err) {
    const hit = await cache.match(SALE_PATH);
    if (!hit) return offlinePage('This page was not opened on this device while online. Connect to the network and open it once.');
    const at = Number(hit.headers.get(CACHED_AT_HEADER) || 0);
    if (!at || Date.now() - at > PAGE_MAX_AGE_MS) {
      return offlinePage('The offline copy of this page is older than 24 hours. Connect to the network to continue.');
    }
    return hit;
  }
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname === SALE_PATH && req.mode === 'navigate') {
    event.respondWith(saleNetworkFirst(req));
    return;
  }
  if (!url.pathname.startsWith('/static/')) return; // everything else: network only
  event.respondWith(
    caches.match(req).then((hit) => hit || fetch(req).then((res) => {
      if (res.ok) {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
      }
      return res;
    }))
  );
});
