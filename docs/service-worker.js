// This file needs to be top-level so that service worker scoping works

const cacheName = "__CACHE_NAME__";
const urlsToCache = ["__URLS_TO_CACHE__"];

// The build step fills in the values above. The dev server copies this file without running that
// step, so an unprocessed worker must remove itself instead of caching the site. Otherwise a
// worker from an earlier build stays in control and keeps serving files from its old cache.
const isUnprocessed = cacheName.includes("CACHE_NAME");

if (isUnprocessed) {
  self.addEventListener('install', () => {
    self.skipWaiting();
  });

  self.addEventListener('activate', event => {
    event.waitUntil(
      caches.keys()
        .then(keys => Promise.all(keys.map(key => caches.delete(key))))
        .then(() => self.registration.unregister())
        .then(() => self.clients.matchAll({ type: 'window' }))
        .then(clients => clients.forEach(client => client.navigate(client.url)))
    );
  });
} else {
  // Install and cache resources
  self.addEventListener('install', event => {
    self.skipWaiting();
    event.waitUntil(
      caches.open(cacheName)
        .then(cache => cache.addAll(urlsToCache))
    );
  });

  // Fetch from cache, fallback to network
  self.addEventListener('fetch', event => {
    event.respondWith(
      caches.match(event.request)
        .then(response => response || fetch(event.request))
    );
  });

  // Clean old caches when new service worker is installed
  self.addEventListener('activate', event => {
    clients.claim();
    const cacheWhitelist = [cacheName];
    event.waitUntil(
      caches.keys()
        .then(keys => Promise.all(
          keys.map(key => {
            if (!cacheWhitelist.includes(key)) {
              return caches.delete(key);
            }
          })
        ))
    );
  });
}
