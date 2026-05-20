const CACHE_VERSION = "bpt-v1";
const SEARCH_CACHE = `${CACHE_VERSION}:search`;
const ASSET_CACHE = `${CACHE_VERSION}:assets`;
const DATA_CACHE = `${CACHE_VERSION}:data`;

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys
      .filter((key) => key.startsWith("bpt-") && !key.startsWith(CACHE_VERSION))
      .map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response.ok || response.type === "opaque") await cache.put(request, response.clone());
  return response;
}

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok || response.type === "opaque") await cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);

  if (url.pathname.includes("/api/v1/search")) {
    event.respondWith(cacheFirst(request, SEARCH_CACHE));
    return;
  }

  if (url.pathname.startsWith("/_next/static/") || request.destination === "image" || request.destination === "font") {
    event.respondWith(cacheFirst(request, ASSET_CACHE));
    return;
  }

  if (url.pathname.includes("/api/v1/")) {
    event.respondWith(networkFirst(request, DATA_CACHE));
  }
});