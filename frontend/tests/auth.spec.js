import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const password = "LocalBrowserTest!8-Password";
const replacement = "DifferentBrowserTest!9-Password";
const emailFor = (info, scenario) => `${info.project.name}.${scenario}@example.invalid`;
const artifactDir = new URL("../../.local/phase3/screenshots/", import.meta.url);

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

async function signIn(page, email, secret = password) {
  await page.goto("/login.html");
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill(secret);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/area-associado\.html$/);
  await expect(page.getByRole("heading", { name: "Olá, Assinante de teste" })).toBeVisible();
}

test("login, persisted session, read-only subscriber area and real logout", async ({ page, context }, info) => {
  await page.goto("/area-associado.html");
  await expect(page).toHaveURL(/login\.html$/);
  await signIn(page, emailFor(info, "reader"));
  for (const title of ["Artigos", "Vídeos", "Áudios"]) await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /publicar|comentar|criar artigo/i })).toHaveCount(0);
  const me = await (await page.request.get("/api/auth/me")).json();
  expect(me.roles).toEqual(["subscriber"]);
  expect(me.capabilities).toEqual({ read_articles: true, watch_videos: true, listen_audio: true, comment: false, create_content: false, edit_content: false, publish_content: false, manage_users: false });
  expect(me.exclusive_content_access).toBe(false);
  expect((await context.cookies()).find((cookie) => cookie.name === "sessionid").httpOnly).toBe(true);
  expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  await page.reload();
  await expect(page.getByRole("heading", { name: "Olá, Assinante de teste" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await mkdir(artifactDir, { recursive: true });
  await page.screenshot({ path: fileURLToPath(new URL(`${info.project.name}-member.png`, artifactDir)), fullPage: true });
  await page.getByRole("button", { name: "Sair", exact: true }).click();
  await expect(page).toHaveURL(/login\.html$/);
  expect((await page.request.get("/api/auth/me")).status()).toBe(403);
  await page.goBack();
  await expect(page.locator(".member-panel")).toHaveCount(0);
});

test("incorrect login, native validation and no external redirect", async ({ page }) => {
  await page.goto("/login.html?next=https://example.invalid");
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByLabel("E-mail", { exact: true })).toBeFocused();
  await page.getByLabel("E-mail", { exact: true }).fill("missing@example.invalid");
  await page.getByLabel("Senha", { exact: true }).fill("OnlyInvalidSyntheticPassword!");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("E-mail ou senha inválidos.");
  await expect(page).toHaveURL(/127\.0\.0\.1:5173\/login\.html/);
});

test("own profile update and rejected permission escalation", async ({ page }, info) => {
  await signIn(page, emailFor(info, "profile"));
  await page.getByRole("link", { name: "Meu perfil" }).click();
  await page.getByLabel("Nome de exibição").fill("Nome atualizado de teste");
  await page.getByRole("button", { name: "Salvar perfil", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Seu perfil público foi atualizado." })).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Nome de exibição")).toHaveValue("Nome atualizado de teste");
  const csrf = await (await page.request.get("/api/auth/csrf")).json();
  const forbidden = await page.request.patch("/api/auth/me", { data: { is_superuser: true, roles: ["administrator"] }, headers: { "X-CSRFToken": csrf.csrf_token } });
  expect(forbidden.status()).toBe(400);
  expect((await (await page.request.get("/api/auth/me")).json()).roles).toEqual(["subscriber"]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await mkdir(artifactDir, { recursive: true });
  await page.screenshot({ path: fileURLToPath(new URL(`${info.project.name}-profile.png`, artifactDir)), fullPage: true });
});

test("password change requires confirmation and revokes another session", async ({ page, browser }, info) => {
  const email = emailFor(info, "password");
  await signIn(page, email);
  const other = await browser.newContext({ baseURL: "http://127.0.0.1:5173" });
  try {
    const csrf = await (await other.request.get("/api/auth/csrf")).json();
    expect((await other.request.post("/api/auth/login", { data: { email, password }, headers: { "X-CSRFToken": csrf.csrf_token } })).status()).toBe(200);
    await page.getByRole("link", { name: "Meu perfil" }).click();
    await page.getByLabel("Senha atual", { exact: true }).fill(password);
    await page.getByLabel("Nova senha", { exact: true }).fill(replacement);
    await page.getByLabel("Confirme a nova senha", { exact: true }).fill("DifferentConfirmation!7");
    await page.getByRole("button", { name: "Alterar senha", exact: true }).click();
    await expect(page.getByRole("alert")).toContainText("não coincidem");
    await page.getByLabel("Confirme a nova senha", { exact: true }).fill(replacement);
    await page.getByRole("button", { name: "Alterar senha", exact: true }).click();
    await expect(page.getByRole("status").filter({ hasText: "Senha alterada." })).toBeVisible();
    expect((await other.request.get("/api/auth/me")).status()).toBe(403);
    expect((await page.request.get("/api/auth/me")).status()).toBe(200);
    await expect(page.getByLabel("Nova senha", { exact: true })).toHaveValue("");
    await page.getByRole("link", { name: "Voltar à minha área" }).click();
    await page.getByRole("button", { name: "Sair", exact: true }).click();
    await expect(page).toHaveURL(/login\.html$/);
    await signIn(page, email, replacement);
  } finally { await other.close(); }
});

test("expired session and unavailable API never display private account information", async ({ page, context }, info) => {
  await signIn(page, emailFor(info, "expiry"));
  await page.route("**/api/auth/me", (route) => route.fulfill({ status: 503, json: { detail: "Unavailable" } }));
  await page.reload();
  await expect(page.getByRole("alert")).toContainText("Não foi possível verificar seu acesso");
  await expect(page.locator(".member-panel")).toHaveCount(0);
  await page.unroute("**/api/auth/me");
  await page.getByRole("button", { name: "Tentar novamente" }).click();
  await expect(page.getByRole("heading", { name: "Olá, Assinante de teste" })).toBeVisible();
  await context.clearCookies();
  await page.reload();
  await expect(page).toHaveURL(/login\.html$/);
  await expect(page.locator(".member-panel")).toHaveCount(0);
});
