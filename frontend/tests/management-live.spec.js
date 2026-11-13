import { test, expect } from "@playwright/test";

test("administrador destaca, home publica e coordenador remove no banco real", async ({ page, context }, testInfo) => {
  const viewport = testInfo.project.name;
  const title = `Destaque real ${viewport}`;
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  async function login(role) {
    await page.goto("/painel/destaques");
    await expect(page).toHaveURL(/login.html$/);
    await page.getByLabel("E-mail", { exact: true }).fill(`${viewport}.${role}@example.invalid`);
    await page.getByLabel("Senha", { exact: true }).fill("PanelBrowserTest!81-Pass");
    await page.getByRole("button", { name: "Entrar", exact: true }).click();
    await expect(page).toHaveURL(/painel\/destaques$/);
  }
  await login("admin");
  const card = page.locator(".management-highlight").filter({ has: page.getByRole("heading", { name: title, exact: true }) });
  await card.getByRole("checkbox", { name: "Exibir em destaque na página inicial" }).check();
  await card.getByRole("spinbutton", { name: "Ordem no carrossel" }).fill("1");
  await card.getByRole("button", { name: "Salvar destaque" }).click();
  await expect(page.getByRole("status").filter({ hasText: "atualizado na página inicial" })).toBeVisible();
  await page.goto("/index.html");
  await expect(page.locator(".mag-feature h2")).toHaveText(title);
  const href = await page.locator(".mag-feature").getByRole("link", { name: "Ler conteúdo" }).getAttribute("href");
  const publicArticle = await page.request.get(`/api/articles/${href.split("/").pop()}`);
  expect((await publicArticle.json()).body).toBeNull();
  await context.clearCookies();
  await login("coordinator");
  await expect(page.getByRole("link", { name: "Usuários", exact: true })).toHaveCount(0);
  expect((await page.request.get("/api/management/users")).status()).toBe(403);
  expect((await page.request.get("/api/management/highlights")).ok()).toBe(true);
  await expect(card.getByRole("checkbox")).toBeChecked();
  await card.getByRole("checkbox").uncheck();
  await card.getByRole("button", { name: "Salvar destaque" }).click();
  await expect(page.getByRole("status").filter({ hasText: "atualizado na página inicial" })).toBeVisible();
  await page.goto("/index.html");
  await expect(page.locator(".mag-feature h2")).toContainText("A Missão do Cristão");
});
