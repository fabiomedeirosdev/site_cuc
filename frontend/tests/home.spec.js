import { test, expect } from "@playwright/test";
import { publicFeed } from "./content-fixtures.mjs";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await context.route("**/api/auth/me", (route) => route.fulfill({ status: 403, json: { detail: "Não autenticado." } }));
  await context.route("**/api/articles?*", (route) => route.fulfill({ json: publicFeed }));
  await context.route("**/api/articles?featured=1&*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/events?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/mural?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/groups?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/facilitators?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/auth/csrf", (route) => route.fulfill({ json: { csrf_token: "test-only" } }));
  await context.route("**/api/newsletter/request", (route) => route.fulfill({ status: 503, json: { detail: "A newsletter está em configuração. Nenhum e-mail foi enviado." } }));
});

test("home: carousel, search, content dialog and newsletter", async ({ page }, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator(".mag-hero-copy > p")).toHaveText("Reflexões, colunas semanais, vídeos e conteúdos exclusivos para fortalecer a sua caminhada com Cristo.");
  await expect(page.locator(".mag-price strong")).toHaveText("R$ 48,00");
  const contributionBanner = page.getByRole("region", { name: "Quero ajudar com um valor maior" });
  const contribution = contributionBanner.getByRole("link", { name: "Clique aqui" });
  await expect(contribution).toBeVisible();
  const whatsapp = new URL(await contribution.getAttribute("href"));
  expect(whatsapp.pathname).toBe("/5511986302883");
  expect(whatsapp.searchParams.get("text")).toBe("Olá, quero ajudar com um valor maior a comunidade.");
  await contributionBanner.screenshot({ path: testInfo.outputPath("contribution-banner.png") });
  await expect(page.locator('link[rel="icon"]')).toHaveAttribute("href", /logos_maria_pomba/);
  if (page.viewportSize().width <= 980) await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  const navigation = page.getByRole("navigation", { name: "Navegação principal" });
  await expect(navigation.getByRole("link", { name: "CUC Online", exact: true })).toBeVisible();
  await expect(navigation.getByRole("link", { name: "Facilitadores", exact: true })).toBeHidden();
  const about = navigation.getByRole("button", { name: "Sobre", exact: true });
  await about.click();
  await expect(navigation.getByRole("link", { name: "Fundadores", exact: true })).toHaveAttribute("href", "/fundadores.html");
  await expect(navigation.getByRole("link", { name: "Facilitadores", exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(about).toHaveAttribute("aria-expanded", "false");
  await expect(about).toBeFocused();
  if (page.viewportSize().width <= 980) await page.getByRole("button", { name: "Fechar menu", exact: true }).click();
  if (page.viewportSize().width === 1440) {
    for (const width of [1101, 1200, 1280, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      const brand = await page.locator(".mag-header .mag-brand").boundingBox();
      const menu = await navigation.boundingBox();
      const actions = await page.locator(".mag-nav-actions").boundingBox();
      expect(brand.x + brand.width).toBeLessThanOrEqual(menu.x);
      expect(menu.x + menu.width).toBeLessThanOrEqual(actions.x);
    }
  }
  await expect(page.locator(".mag-feature h2")).toContainText("A Missão do Cristão");
  await page.getByRole("button", { name: "Próximo destaque" }).click();
  await expect(page.locator(".mag-feature h2")).toContainText("Uma só missão");
  await expect(page.getByRole("button", { name: "Ver destaque 2" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Destaque anterior" }).click();
  await expect(page.locator(".mag-feature h2")).toContainText("A Missão do Cristão");
  await page.getByRole("button", { name: "Buscar na comunidade online" }).click();
  await page.getByRole("searchbox").fill("maria");
  await expect(page.locator(".mag-publication")).toHaveCount(1);
  await expect(page.locator(".mag-publication > a")).toHaveAttribute("href", "/conteudos/901");
  await page.getByRole("searchbox").fill("inexistente");
  await expect(page.getByRole("status")).toContainText("Nenhum conteúdo encontrado");
  await page.getByRole("button", { name: "Fechar busca" }).click();
  await expect(page.locator(".mag-publication")).toHaveCount(3);
  await page.getByRole("textbox", { name: "Seu e-mail" }).fill("teste@example.invalid");
  await page.getByRole("checkbox", { name: /Quero receber a newsletter semanal/ }).check();
  await page.getByRole("button", { name: "Inscrever-se" }).click();
  await expect(page.locator(".mag-newsletter").getByRole("status")).toContainText("Nenhum e-mail foi enviado");
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  if (page.viewportSize().width <= 980) await page.getByRole("button", { name: "Abrir menu", exact: true }).click();
  await about.click();
  await navigation.getByRole("link", { name: "Facilitadores", exact: true }).click();
  await expect(page).toHaveURL(/facilitadores.html$/);
  await expect(page.getByRole("heading", { name: "Facilitadores", exact: true })).toBeVisible();
});
