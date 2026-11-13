import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const confirmations = JSON.parse(process.env.CUC_PROFILE_CONFIRMATIONS || "{}");
const password = "PublicProfilesBrowser!81-Pass";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

async function login(page, viewport, role) {
  await page.goto("/perfil.html");
  await expect(page).toHaveURL(/login.html$/);
  await page.getByLabel("E-mail", { exact: true }).fill(`${viewport}.${role}@example.invalid`);
  await page.getByLabel("Senha", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/perfil.html$/);
}

async function savePresentation(page, name) {
  await page.getByRole("textbox", { name: "Nome de exibição", exact: true }).fill(name);
  await page.getByRole("textbox", { name: "Biografia", exact: true }).fill("Uma caminhada de fé e serviço em comunidade.");
  await page.getByRole("textbox", { name: "Meu site", exact: true }).fill("https://example.org");
  await page.getByRole("textbox", { name: "Vídeo de apresentação no YouTube", exact: true }).fill("https://youtu.be/abcdefghijk");
  await page.getByLabel("Minha foto", { exact: true }).setInputFiles(process.env.CUC_PROFILE_PHOTO);
}

async function noOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

test("coordenador publica foto, apresentação, contato e vídeo visíveis para visitantes", async ({ page, browser }, info) => {
  const viewport = info.project.name;
  const name = `Pessoa Coordenadora ${viewport}`;
  await login(page, viewport, "coordinator");
  await expect(page.getByText("Coordenador", { exact: true })).toBeVisible();
  await savePresentation(page, name);
  await page.getByRole("textbox", { name: "Telefone de contato público", exact: true }).fill("+55 (11) 99999-9999");
  await page.getByRole("button", { name: "Salvar perfil", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Seu perfil público foi atualizado" })).toBeVisible();
  await noOverflow(page);
  const href = await page.getByRole("link", { name: "Ver meu perfil público" }).getAttribute("href");
  const guest = await browser.newContext({ baseURL: "http://127.0.0.1:5184", viewport: page.viewportSize() });
  try {
    await guest.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
    const other = await guest.newPage();
    await other.goto(href);
    await expect(other.getByRole("heading", { name, exact: true })).toBeVisible();
    await expect(other.getByRole("img", { name: `Foto de ${name}`, exact: true })).toBeVisible();
    await expect(other.getByRole("link", { name: "+55 (11) 99999-9999", exact: true })).toHaveAttribute("href", "tel:+5511999999999");
    await expect(other.locator("iframe")).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/abcdefghijk");
    await expect(other.getByText(`${viewport}.coordinator@example.invalid`, { exact: true })).toHaveCount(0);
    await noOverflow(other);
    await mkdir("../.local/profiles/screenshots", { recursive: true });
    await other.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
    await other.screenshot({ path: `../.local/profiles/screenshots/${viewport}-perfil-publico.png`, fullPage: true });
    await other.goto("/perfis.html");
    await other.getByRole("searchbox", { name: "Buscar por nome", exact: true }).fill(name);
    await other.getByRole("button", { name: "Buscar", exact: true }).click();
    await other.getByRole("combobox", { name: "Função na comunidade", exact: true }).selectOption("coordinator");
    await expect(other.locator(".profile-person-card")).toHaveCount(1);
    await expect(other.locator(".profile-person-card")).toContainText(name);
  } finally { await guest.close(); }
});

test("assinante publica perfil sem telefone e solicita e-mail sem alterar o login antes da confirmação", async ({ page }, info) => {
  const viewport = info.project.name;
  await login(page, viewport, "subscriber");
  await expect(page.getByText("Assinante", { exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Telefone de contato público", exact: true })).toHaveCount(0);
  await savePresentation(page, `Pessoa Assinante ${viewport}`);
  await page.getByRole("button", { name: "Salvar perfil", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Seu perfil público foi atualizado" })).toBeVisible();
  const csrf = (await (await page.request.get("/api/auth/csrf")).json()).csrf_token;
  expect((await page.request.patch("/api/auth/me", { data: { phone: "11999999999" }, headers: { "X-CSRFToken": csrf } })).status()).toBe(403);
  await page.getByRole("textbox", { name: "Novo e-mail", exact: true }).fill(`new.${viewport}.subscriber@example.invalid`);
  await page.getByLabel("Senha atual para alterar o e-mail", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Confirmar novo e-mail", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Confira o novo endereço de e-mail" })).toBeVisible();
  expect((await (await page.request.get("/api/auth/me")).json()).email).toBe(`${viewport}.subscriber@example.invalid`);
  await noOverflow(page);
});

test("desenvolvedor tem função fixa e confirma novo e-mail por link de uso único", async ({ page }, info) => {
  const viewport = info.project.name;
  await login(page, viewport, "developer");
  await expect(page.getByText("Desenvolvedor", { exact: true })).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Telefone de contato público", exact: true })).toBeVisible();
  await expect(page.getByRole("combobox")).toHaveCount(0);
  await page.goto("/painel");
  await expect(page.locator(".management-profile")).toContainText("Desenvolvedor");
  await page.goto(`/confirmar-email.html#token=${confirmations[viewport]}`);
  await expect(page).toHaveURL(/confirmar-email.html$/);
  await page.getByRole("button", { name: "Confirmar alteração de e-mail", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("E-mail confirmado e atualizado");
  expect((await (await page.request.get("/api/auth/me")).json()).email).toBe(`confirmed.${viewport}@example.invalid`);
  const publicId = (await (await page.request.get("/api/auth/me")).json()).public_id;
  const publicProfile = await (await page.request.get(`/api/profiles/${publicId}`)).json();
  expect(publicProfile.email).toBeUndefined();
  await noOverflow(page);
});
