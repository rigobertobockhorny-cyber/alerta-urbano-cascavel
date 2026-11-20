// Service Worker - Alerta Urbano v3.1 (Anti-Cache Force Update)
const CACHE_NAME = 'alerta-urbano-v31';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.map(k => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  // Always go to network first to ensure real-time map, zero stale cache
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
