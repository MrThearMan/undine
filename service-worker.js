// This file needs to be top-level so that service worker scoping works

const cacheName = "bdffbaf1c3f34890a35849c86c89d714";
const urlsToCache = [
  "",
  "404.html",
  "css/docs.css",
  "css/pygments.css",
  "css/theme.css",
  "css/theme_extra.css",
  "js/docs.js",
  "js/theme.js",
  "js/theme_extra.js",
  "img/favicon.ico",
  "search.html",
  "search/lunr.js",
  "search/main.js",
  "search/search_index.json",
  "search/worker.js",
  "getting-started/",
  "tutorial/",
  "schema/",
  "queries/",
  "mutations/",
  "filtering/",
  "ordering/",
  "pagination/",
  "subscriptions/",
  "global-object-ids/",
  "file-upload/",
  "persisted-documents/",
  "interfaces/",
  "unions/",
  "scalars/",
  "directives/",
  "hacking-undine/",
  "optimizer/",
  "async/",
  "dataloaders/",
  "lifecycle-hooks/",
  "validation-rules/",
  "integrations/",
  "settings/",
  "faq/",
  "contributing/"
];

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
