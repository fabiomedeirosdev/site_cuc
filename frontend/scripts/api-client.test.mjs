import assert from "node:assert/strict";
import test from "node:test";
import { createApiClient } from "../src/api-client.js";

test("uses the local proxy and accepts an abort signal", async () => {
  const signal = new AbortController().signal;
  const api = createApiClient({
    fetchImpl: async (url, options) => {
      assert.equal(url, "/api/health");
      assert.equal(options.signal, signal);
      assert.equal(options.headers.Accept, "application/json");
      return new Response(JSON.stringify({ status: "ok" }));
    },
  });
  assert.deepEqual(await api.getHealth({ signal }), { status: "ok" });
});

test("supports an explicit API origin without duplicated slashes", async () => {
  const api = createApiClient({
    baseUrl: "http://127.0.0.1:8000/",
    fetchImpl: async (url) => {
      assert.equal(url, "http://127.0.0.1:8000/api/ready");
      return new Response(JSON.stringify({ status: "ok", database: "ok" }));
    },
  });
  assert.equal((await api.getReadiness()).database, "ok");
});

test("rejects HTTP failures instead of treating them as success", async () => {
  const api = createApiClient({ fetchImpl: async () => new Response("{}", { status: 503 }) });
  await assert.rejects(api.getReadiness(), /503/);
});

test("propagates network errors", async () => {
  const api = createApiClient({ fetchImpl: async () => { throw new TypeError("offline"); } });
  await assert.rejects(api.getHealth(), /offline/);
});

test("login obtains CSRF and sends credentials only in a JSON request with cookies", async () => {
  const calls = [];
  const api = createApiClient({ fetchImpl: async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify(url.endsWith("/csrf") ? { csrf_token: "masked-test-token" } : { user: { id: 1 } }));
  } });
  await api.login({ email: "teste@example.invalid", password: "OnlySyntheticPassword!" });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].url, "/api/auth/csrf");
  assert.equal(calls[1].url, "/api/auth/login");
  assert.equal(calls[1].options.headers["X-CSRFToken"], "masked-test-token");
  assert.equal(calls[1].options.credentials, "include");
  assert.equal(calls[1].options.cache, "no-store");
  assert.equal(calls[1].options.method, "POST");
  assert.equal(JSON.parse(calls[1].options.body).email, "teste@example.invalid");
});

test("profile and password writes refresh CSRF and keep the correct verbs", async () => {
  const writes = [];
  const api = createApiClient({ fetchImpl: async (url, options) => {
    if (options.method !== "GET") writes.push([url, options.method]);
    return new Response(JSON.stringify(url.endsWith("/csrf") ? { csrf_token: "test-token" } : {}));
  } });
  await api.updateProfile({ display_name: "Teste" });
  await api.changePassword({ current_password: "OnlyTest!", new_password: "AnotherTest!" });
  await api.logout();
  assert.deepEqual(writes, [["/api/auth/me", "PATCH"], ["/api/auth/password", "POST"], ["/api/auth/logout", "POST"]]);
});

test("API validation errors preserve status and a useful message", async () => {
  const api = createApiClient({ fetchImpl: async () => new Response(JSON.stringify({ detail: "E-mail ou senha inválidos." }), { status: 400 }) });
  await assert.rejects(api.getMe(), (error) => error.status === 400 && error.message === "E-mail ou senha inválidos.");
});

test("concurrent anonymous writes share CSRF acquisition then refresh after completion", async () => {
  let reads = 0;
  const sent = [];
  const api = createApiClient({ fetchImpl: async (url, options) => {
    if (url.endsWith("/csrf")) {
      reads += 1;
      await new Promise((resolve) => setTimeout(resolve, 5));
      return new Response(JSON.stringify({ csrf_token: `token-${reads}` }));
    }
    sent.push(options.headers["X-CSRFToken"]);
    return new Response("{}");
  } });
  await Promise.all([api.checkInvitation("test-invitation"), api.checkInvitation("test-invitation")]);
  assert.equal(reads, 1);
  assert.deepEqual(sent, ["token-1", "token-1"]);
  await api.completeInvitation({ token: "test-invitation" });
  assert.equal(reads, 2);
  assert.equal(sent[2], "token-2");
});
