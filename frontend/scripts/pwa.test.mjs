import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";
import { applicationServerKey, clearPushNotifications, disableNotifications, enableNotifications, isInstalled, supportsPush, syncPushSubscription } from "../src/pwa.js";

const publicRoot = new URL("../public/", import.meta.url);
const workerSource = await readFile(new URL("sw.js", publicRoot), "utf8");

function worker({ network = async () => "network", windows = [] } = {}) {
  const handlers = {};
  const shown = [];
  const opened = [];
  const cached = [];
  const removed = [];
  const self = {
    location: { origin: "https://rhemacuc.com.br" },
    addEventListener: (name, callback) => { handlers[name] = callback; },
    registration: { showNotification: async (...args) => { shown.push(args); } },
    clients: { claim: async () => {}, matchAll: async () => windows, openWindow: async (url) => { opened.push(url); } },
  };
  vm.runInNewContext(workerSource, { self, URL, fetch: network, caches: {
    open: async () => ({ addAll: async (urls) => { cached.push(...urls); } }),
    match: async (url) => url === "/offline.html" ? "offline-page" : undefined,
    keys: async () => ["rhema-public-v0", "other-application-cache"],
    delete: async (key) => { removed.push(key); },
  } });
  async function dispatch(name, fields = {}) {
    let promise;
    handlers[name]({ ...fields, waitUntil: (value) => { promise = value; }, respondWith: (value) => { promise = value; } });
    return promise;
  }
  return { dispatch, shown, opened, cached, removed };
}

test("manifest and supplied icon variants identify RHEMA CUC", async () => {
  const manifest = JSON.parse(await readFile(new URL("manifest.webmanifest", publicRoot), "utf8"));
  assert.equal(manifest.name, "RHEMA CUC");
  assert.equal(manifest.short_name, "RHEMA CUC");
  assert.equal(manifest.display, "standalone");
  for (const icon of [...manifest.icons, { src: "/icons/apple-touch-icon.png", sizes: "180x180" }]) {
    const bytes = await readFile(new URL(icon.src.slice(1), publicRoot));
    assert.equal(bytes.subarray(1, 4).toString(), "PNG");
    assert.equal(`${bytes.readUInt32BE(16)}x${bytes.readUInt32BE(20)}`, icon.sizes);
  }
});

test("worker caches public offline assets and preserves unrelated caches", async () => {
  const sw = worker();
  await sw.dispatch("install");
  assert.ok(sw.cached.includes("/offline.html"));
  assert.ok(sw.cached.every((path) => path === "/offline.html" || path.startsWith("/icons/")));
  await sw.dispatch("activate");
  assert.deepEqual(sw.removed, ["rhema-public-v0"]);
});

test("offline fallback never caches account, article, or API responses", async () => {
  const sw = worker({ network: async () => { throw new Error("offline"); } });
  for (const path of ["/conteudos/22", "/area-associado.html", "/painel"]) {
    assert.equal(await sw.dispatch("fetch", { request: { url: `https://rhemacuc.com.br${path}`, method: "GET", mode: "navigate" } }), "offline-page");
  }
  for (const path of ["/api/auth/me", "/api/articles/22", "/admin/", "/media/private.jpg"]) {
    assert.equal(await sw.dispatch("fetch", { request: { url: `https://rhemacuc.com.br${path}`, method: "GET", mode: path.startsWith("/media") ? "cors" : "navigate" } }), undefined);
  }
  assert.deepEqual(sw.cached, []);
});

test("push works in a worker with no open site and repeated tags replace notifications", async () => {
  const sw = worker();
  const data = { body: "Uma nova publicação está disponível na comunidade.", tag: "rhema-article-22", url: "/conteudos/22" };
  await sw.dispatch("push", { data: { json: () => data } });
  await sw.dispatch("push", { data: { json: () => data } });
  assert.equal(sw.shown[0][0], "RHEMA CUC");
  assert.equal(sw.shown[0][1].tag, sw.shown[1][1].tag);
  assert.equal(sw.shown[0][1].renotify, false);
  let closed = false;
  await sw.dispatch("notificationclick", { notification: { data: sw.shown[0][1].data, close: () => { closed = true; } } });
  assert.equal(closed, true);
  assert.deepEqual(sw.opened, ["https://rhemacuc.com.br/conteudos/22"]);
});

test("notification clicks cannot open foreign or administrative URLs", async () => {
  const sw = worker();
  for (const url of ["https://evil.invalid", "javascript:alert(1)", "/admin/", "http://[invalid"]) {
    await sw.dispatch("notificationclick", { notification: { data: { url }, close() {} } });
  }
  assert.ok(sw.opened.every((url) => url === "https://rhemacuc.com.br/index.html"));
});

test("existing app window is reused for a notification", async () => {
  let navigated, focused = false;
  const sw = worker({ windows: [{ url: "https://rhemacuc.com.br/index.html", navigate: async (url) => { navigated = url; }, focus: async () => { focused = true; } }] });
  await sw.dispatch("notificationclick", { notification: { data: { url: "/agenda.html#evento-2" }, close() {} } });
  assert.equal(navigated, "https://rhemacuc.com.br/agenda.html#evento-2");
  assert.equal(focused, true);
  assert.deepEqual(sw.opened, []);
});

test("browser capability detection is safe outside a browser and decodes VAPID keys", () => {
  assert.equal(isInstalled(), false);
  assert.equal(supportsPush(), false);
  assert.deepEqual([...applicationServerKey("AQID-w")], [1, 2, 3, 251]);
});

test("push subscription requires a click, syncs existing consent, and cancels even with API offline", async () => {
  const originals = new Map();
  const storage = new Map();
  const calls = [];
  let subscription = null;
  const makeSubscription = () => ({
    endpoint: "https://fcm.googleapis.com/send/test",
    toJSON: () => ({ endpoint: "https://fcm.googleapis.com/send/test", keys: { p256dh: "test-key", auth: "test-auth" } }),
    unsubscribe: async () => { calls.push("unsubscribe"); subscription = null; return true; },
  });
  const registration = { pushManager: {
    getSubscription: async () => subscription,
    subscribe: async (options) => { calls.push("subscribe"); assert.equal(options.userVisibleOnly, true); subscription = makeSubscription(); return subscription; },
  }, getNotifications: async () => [{ close: () => { calls.push("close-notification"); } }] };
  const notification = { permission: "default", requestPermission: async () => { calls.push("permission"); notification.permission = "granted"; return "granted"; } };
  const replacements = {
    isSecureContext: true, PushManager: class {}, Notification: notification,
    navigator: { serviceWorker: { register: async () => registration, ready: Promise.resolve(registration) } },
    localStorage: { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
  };
  for (const [key, value] of Object.entries(replacements)) {
    originals.set(key, Object.getOwnPropertyDescriptor(globalThis, key));
    Object.defineProperty(globalThis, key, { configurable: true, value });
  }
  const saved = [];
  const api = {
    getPushConfig: async () => { calls.push("config"); return { enabled: true, public_key: "AQID" }; },
    savePushSubscription: async (data) => { saved.push(data); },
    deletePushSubscription: async () => { calls.push("delete"); throw new Error("API offline"); },
  };
  try {
    await syncPushSubscription(api);
    assert.deepEqual(calls, []);
    await enableNotifications(api);
    assert.deepEqual(calls.slice(0, 3), ["permission", "config", "subscribe"]);
    assert.match(saved[0].device_token, /^[A-Za-z0-9_-]{43}$/);
    await syncPushSubscription(api);
    assert.equal(saved.length, 2);
    assert.equal(saved[0].device_token, saved[1].device_token);
    assert.equal(calls.filter((call) => call === "permission").length, 1);
    assert.equal(calls.filter((call) => call === "subscribe").length, 1);
    await disableNotifications(api);
    assert.equal(subscription, null);
    assert.deepEqual(calls.slice(-2), ["delete", "unsubscribe"]);
    await clearPushNotifications();
    assert.equal(calls.at(-1), "close-notification");
    api.savePushSubscription = async () => { throw new Error("Registration failed"); };
    await assert.rejects(enableNotifications(api), /Registration failed/);
    assert.equal(subscription, null);
  } finally {
    for (const [key, descriptor] of originals) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor); else delete globalThis[key];
    }
  }
});
