const TILE_CACHE_NAME = "disaster-map-tiles-v1";
const TILE_HOSTS = [
  "tile.openstreetmap.org",
  "a.tile.openstreetmap.org",
  "b.tile.openstreetmap.org",
  "c.tile.openstreetmap.org",
  "basemaps.cartocdn.com",
  "server.arcgisonline.com",
];

const EMPTY_TILE_B64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO9xv2QAAAAASUVORK5CYII=";

function isTileRequest(request) {
  try {
    const url = new URL(request.url);
    if (request.destination === "image" && TILE_HOSTS.includes(url.hostname)) return true;
    if (TILE_HOSTS.includes(url.hostname) && /\/tile\/|\/rastertiles\/|\/\d+\/\d+\/\d+/.test(url.pathname)) {
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

function postToClient(clientId, message) {
  if (!clientId) {
    return self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      clients.forEach((client) => client.postMessage(message));
    });
  }
  return self.clients.get(clientId).then((client) => {
    if (client) client.postMessage(message);
  });
}

async function cacheFirstTileResponse(request) {
  const cache = await caches.open(TILE_CACHE_NAME);
  const cached = await cache.match(request, { ignoreVary: true, ignoreSearch: false });
  if (cached) return cached;

  try {
    const response = await fetch(request);
    // Accept only successful image-like responses into tile cache.
    if (response && response.ok) {
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("image")) {
        await cache.put(request, response.clone());
      }
    }
    return response;
  } catch {
    return new Response(Uint8Array.from(atob(EMPTY_TILE_B64), (c) => c.charCodeAt(0)), {
      status: 200,
      headers: { "Content-Type": "image/png" },
    });
  }
}

async function predownloadTiles(urls, clientId) {
  const uniqueUrls = [...new Set(urls)].filter((url) => typeof url === "string" && url.startsWith("http"));
  const total = uniqueUrls.length;
  const cache = await caches.open(TILE_CACHE_NAME);
  let completed = 0;
  let failed = 0;
  let cursor = 0;
  const concurrency = 6;

  async function worker() {
    while (cursor < total) {
      const idx = cursor++;
      const url = uniqueUrls[idx];
      try {
        const req = new Request(url, {
          mode: "cors",
          credentials: "omit",
          cache: "no-store",
          referrerPolicy: "strict-origin-when-cross-origin",
        });
        const res = await fetch(req);
        if (res && res.ok) {
          const contentType = res.headers.get("content-type") || "";
          if (contentType.includes("image")) {
            await cache.put(req, res.clone());
            completed += 1;
          } else {
            failed += 1;
          }
        } else {
          failed += 1;
        }
      } catch {
        failed += 1;
      }

      if ((completed + failed) % 15 === 0 || completed + failed === total) {
        await postToClient(clientId, {
          type: "TILE_DOWNLOAD_PROGRESS",
          completed,
          failed,
          total,
        });
      }
    }
  }

  await Promise.all(Array.from({ length: Math.min(concurrency, total || 1) }, () => worker()));
  await postToClient(clientId, {
    type: "TILE_DOWNLOAD_DONE",
    completed,
    failed,
    total,
  });
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(Promise.resolve());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  if (!isTileRequest(event.request)) return;
  event.respondWith(cacheFirstTileResponse(event.request));
});

self.addEventListener("message", (event) => {
  const data = event.data || {};
  if (data.type === "DOWNLOAD_TILES" && Array.isArray(data.urls)) {
    event.waitUntil(predownloadTiles(data.urls, event.source && event.source.id));
  } else if (data.type === "CLEAR_TILE_CACHE") {
    event.waitUntil(caches.delete(TILE_CACHE_NAME));
  }
});
