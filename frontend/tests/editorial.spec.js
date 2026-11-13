import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

async function login(page, project, role) {
  await page.goto("/gestao-grupos.html");
  await expect(page).toHaveURL(/login.html$/);
  await page.getByLabel("E-mail", { exact: true }).fill(`${project}.${role}@example.invalid`);
  await page.getByLabel("Senha", { exact: true }).fill("LocalEditorialTest!8-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/gestao-grupos.html$/);
}

test("public directory, group details, empty authors and protected management", async ({ page }, testInfo) => {
  await page.goto("/grupos.html");
  await page.locator(`a[href="/grupos/e2e-${testInfo.project.name}"]`).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(`Grupo ${testInfo.project.name}`);
  await expect(page.getByText("A equipe será apresentada aqui em breve.")).toBeVisible();
  expect((await page.request.get("/api/editorial/groups")).status()).toBe(403);
  await page.getByRole("link", { name: "Facilitadores", exact: true }).click();
  await expect(page.getByText(/Os facilitadores serão apresentados/)).toBeVisible();
  await login(page, testInfo.project.name, "reader");
  await expect(page.getByText(/Nenhum grupo disponível para gestão/)).toBeVisible();
  expect(await page.locator("input").count()).toBe(0);
});

test("coordinator adds, publishes presentation and removes only a group link", async ({ page }, testInfo) => {
  const project = testInfo.project.name;
  await login(page, project, "coordinator");
  await page.locator(".editorial-group-select select").selectOption(`e2e-${project}`);
  await expect(page.locator(".editorial-group-select select")).toHaveValue(`e2e-${project}`);
  await page.getByLabel("E-mail da conta").fill(`${project}.columnist@example.invalid`);
  await page.getByRole("button", { name: "Adicionar vínculo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Vínculo adicionado" })).toBeVisible();
  const member = page.locator(".editorial-member").filter({ has: page.getByRole("heading", { name: "Facilitador de teste" }) });
  await member.locator("summary").click();
  await member.getByLabel("Apresentação", { exact: true }).fill("Apresentação pública de teste.");
  await member.getByLabel("Exibir nome e apresentação na página pública").check();
  await member.getByRole("button", { name: "Salvar vínculo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Vínculo atualizado" })).toBeVisible();
  const publicGroup = await page.request.get(`/api/groups/e2e-${project}`);
  expect((await publicGroup.json()).team).toEqual([{ display_name: "Facilitador de teste", role: "columnist", biography: "Apresentação pública de teste.", avatar_url: null, profile_url: expect.stringMatching(/^\/perfis\/[a-f0-9-]+$/) }]);
  await page.goto(`/grupos/e2e-${project}`);
  await expect(page.getByText("Apresentação pública de teste.")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.goto("/gestao-grupos.html");
  await page.locator(".editorial-group-select select").selectOption(`e2e-${project}`);
  await member.locator("summary").click();
  await member.getByRole("button", { name: "Remover vínculo" }).click();
  await member.getByRole("button", { name: "Confirmar remoção" }).click();
  await expect(page.getByRole("status").filter({ hasText: "A conta foi preservada" })).toBeVisible();
  await expect(page.locator(".editorial-member")).toHaveCount(1);
  await mkdir("../.local/phase4/screenshots", { recursive: true });
  await page.screenshot({ path: `../.local/phase4/screenshots/${project}-gestao.png`, fullPage: true });
});

test("administrator assigns a coordinator without granting account privileges", async ({ page }, testInfo) => {
  const project = testInfo.project.name;
  await login(page, project, "admin");
  await page.locator(".editorial-group-select select").selectOption(`e2e-${project}`);
  await page.getByLabel("E-mail da conta").fill(`${project}.reader@example.invalid`);
  await page.locator(".editorial-add-form").getByLabel("Função").selectOption("coordinator");
  await page.getByRole("button", { name: "Adicionar vínculo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Vínculo adicionado" })).toBeVisible();
  await expect(page.locator(".editorial-member").filter({ hasText: "Leitor de teste" })).toContainText("Coordenador");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("coordinator creates a facilitator access without technical privileges", async ({ page }, info) => {
  const project = info.project.name;
  await login(page, project, "coordinator");
  await page.getByLabel("Criar acesso para um novo facilitador").check();
  await page.getByLabel("Nome do facilitador", { exact: true }).fill("Novo facilitador de teste");
  await page.getByLabel("Senha inicial", { exact: true }).fill("InitialFacilitator!81-Password");
  await page.getByLabel("E-mail da conta").fill(`created.${project}@example.invalid`);
  await page.getByRole("button", { name: "Adicionar vínculo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Vínculo adicionado" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Novo facilitador de teste" })).toBeVisible();
  const csrf = await (await page.request.get("/api/auth/csrf")).json();
  const loginResponse = await page.request.post("/api/auth/login", { headers: { "X-CSRFToken": csrf.csrf_token }, data: { email: `created.${project}@example.invalid`, password: "InitialFacilitator!81-Password" } });
  expect(loginResponse.status()).toBe(200);
  const user = (await loginResponse.json()).user;
  expect(user.capabilities.create_content).toBe(true);
  expect(user.capabilities.manage_users).toBe(false);
  expect(user.can_manage_editorial_groups).toBe(false);
  expect(user.editorial_groups).toHaveLength(1);
});
