/* Only this public offline page and icons are cached. Never cache API responses,
   account pages, uploaded media, or subscriber content. */
const CACHE = "rhema-public-v1";
const PUBLIC_FILES = ["/offline.html", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(PUBLIC_FILES)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("rhema-public-") && key !== CACHE).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin !== self.location.origin || event.request.method !== "GET") return;
  if (event.request.mode === "navigate" && !url.pathname.startsWith("/api/") && !url.pathname.startsWith("/admin/")) {
    event.respondWith(fetch(event.request).catch(() => caches.match("/offline.html")));
  } else if (PUBLIC_FILES.includes(url.pathname)) {
    event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
  }
});

function notificationUrl(value) {
  try {
    const url = new URL(value || "/index.html", self.location.origin);
    const allowed = url.pathname === "/index.html" || /^\/conteudos\/\d+$/.test(url.pathname) || url.pathname === "/agenda.html";
    if (url.origin === self.location.origin && allowed) return url.href;
  } catch { /* Ignore invalid notification links. */ }
  return `${self.location.origin}/index.html`;
}

self.addEventListener("push", (event) => {
  let data = {};
  try { data = event.data?.json() || {}; } catch { /* Show a generic notification. */ }
  event.waitUntil(self.registration.showNotification("RHEMA CUC", {
    body: data.body || "Há novidades na Comunidade Unidos em Cristo.",
    icon: "/icons/icon-192.png",
    tag: data.tag || "rhema-novidades",
    renotify: false,
    data: { url: notificationUrl(data.url) },
  }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = notificationUrl(event.notification.data?.url);
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (windows) => {
    const client = windows.find((window) => new URL(window.url).origin === self.location.origin);
    if (client) { await client.navigate(url); return client.focus(); }
    return self.clients.openWindow(url);
  }));
});
