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


test("image URLs use the API origin across nested lists without changing other links", async () => {
  const api = createApiClient({ mediaBaseUrl: "https://api.rhemacuc.com.br/", fetchImpl: async () => new Response(JSON.stringify({
    results: [{ cover_url: "/api/public-images/covers/test.webp", avatar_url: "/api/profiles/id/photo?v=123", photo_url: "/media/old.jpg", image_url: "/api/communication-images/notices/1", profile_url: "/perfis/id", website: "https://example.com" }],
    cover_url: null, photo_url: "https://cdn.example.com/photo.jpg",
  })) });
  const data = await api.getArticles();
  assert.equal(data.results[0].cover_url, "https://api.rhemacuc.com.br/api/public-images/covers/test.webp");
  assert.equal(data.results[0].avatar_url, "https://api.rhemacuc.com.br/api/profiles/id/photo?v=123");
  assert.equal(data.results[0].photo_url, "https://api.rhemacuc.com.br/media/old.jpg");
  assert.equal(data.results[0].image_url, "https://api.rhemacuc.com.br/api/communication-images/notices/1");
  assert.equal(data.results[0].profile_url, "/perfis/id");
  assert.equal(data.results[0].website, "https://example.com");
  assert.equal(data.cover_url, null);
  assert.equal(data.photo_url, "https://cdn.example.com/photo.jpg");
});

test("uploaded cover preview uses the image origin", async () => {
  const api = createApiClient({ mediaBaseUrl: "https://api.rhemacuc.com.br", fetchImpl: async (url) => new Response(JSON.stringify(
    url.endsWith("/csrf") ? { csrf_token: "test" } : { id: "cover", url: "/api/public-images/covers/photo.webp" }
  )) });
  const cover = await api.uploadCover(new Blob(["image"], { type: "image/webp" }));
  assert.equal(cover.url, "https://api.rhemacuc.com.br/api/public-images/covers/photo.webp");
});

test("image origins preserve local proxy and configured hosting", async () => {
  const { mediaOrigin, mediaUrl } = await import("../src/media-url.js");
  assert.equal(mediaOrigin("", "localhost"), "");
  assert.equal(mediaOrigin("", "127.0.0.1"), "");
  assert.equal(mediaOrigin("", "rhemacuc.com.br"), "https://api.rhemacuc.com.br");
  assert.equal(mediaOrigin("https://custom.example/", "rhemacuc.com.br"), "https://custom.example");
  assert.equal(mediaUrl("blob:preview", "https://api.example"), "blob:preview");
  assert.equal(mediaUrl("/assets/logo.png", "https://api.example"), "/assets/logo.png");
});
