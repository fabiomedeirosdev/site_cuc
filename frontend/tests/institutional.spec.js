import { test, expect } from "@playwright/test";
import { readFile, mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { publicFeed } from "./content-fixtures.mjs";

const root = new URL("../../", import.meta.url);
const artifactDir = new URL(".local/phase2/screenshots/", root);
const pages = [
  "index.html", "login.html", "cadastro.html", "recuperar-senha.html",
  "acesso-negado.html", "link-expirado.html",
  "pagamento-sucesso.html", "pagamento-pendente.html", "pagamento-cancelado.html",
  "politica-privacidade.html", "termos.html",
];

// No external service is contacted, including fonts, videos, email or payment.
test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    return url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
  // Public-page regression uses an anonymous session; real auth is tested separately.
  await context.route("**/api/auth/me", (route) => route.fulfill({ status: 403, json: { detail: "Não autenticado." } }));
  await context.route("**/api/billing/config", (route) => route.fulfill({ json: { available: false, sandbox: true, amount: 4820, legal_version: "2026-11-12-v1", merchant: {} } }));
  await context.route("**/api/auth/csrf", (route) => route.fulfill({ json: { csrf_token: "test-only" } }));
  await context.route("**/api/billing/invitation/resend", (route) => route.fulfill({ json: { detail: "Se houver uma assinatura válida, enviaremos um novo link." } }));
  await context.route("**/api/articles?*", (route) => route.fulfill({ json: publicFeed }));
  await context.route("**/api/events?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  await context.route("**/api/mural?*", (route) => route.fulfill({ json: { count: 0, next: null, previous: null, results: [] } }));
  // A integração editorial real usa o PostgreSQL temporário em editorial.spec.js.
  await context.route("**/api/groups?*", (route) => route.fulfill({ json: { count: 4, next: null, previous: null, results: [
    { name: "Rhematerapia", slug: "rhematerapia", cover: "heart" },
    { name: "Restaura-me", slug: "restaura-me", cover: "prayer" },
    { name: "Promoção à Vida", slug: "promocao-a-vida", cover: "family" },
    { name: "Grupo C.U.R.A.", slug: "grupo-cura", cover: "headquarters" },
  ] } }));
});

for (const filename of pages) {
  test(`${filename}: original content, assets, layout and title`, async ({ page, context }, testInfo) => {
    const errors = [];
    const failedLocalResponses = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("response", (response) => {
      if (response.url().startsWith("http://127.0.0.1") && response.status() >= 400 && !response.url().endsWith("/api/auth/me")) {
        failedLocalResponses.push(`${response.status()} ${response.url()}`);
      }
    });
    const html = await readFile(new URL(filename, root), "utf8");
    const response = await page.goto(`/${filename}`);
    expect(response.status()).toBe(200);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("h1")).toHaveCount(1);
    if (filename === "login.html") await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
    const parity = await page.evaluate((original) => {
      const legacy = new DOMParser().parseFromString(original, "text/html");
      const selectors = "main h1, main h2, main h3, main p, main small, main li, main cite, main .price, main .card-icon, main .plan-badge, footer h2, footer p, footer .social a, footer .footer-logo-mark";
      const text = (node) => [...node.querySelectorAll(selectors)]
        .map((element) => element.textContent.replace(/\s+/g, "").normalize("NFC"))
        .filter(Boolean);
      return {
        expected: text(legacy), actual: text(document),
        title: legacy.title,
        originalForms: [...legacy.querySelectorAll("input")].map((input) => [input.name, input.type, input.required, input.minLength, input.autocomplete]),
        forms: [...document.querySelectorAll("input")].map((input) => [input.name, input.type, input.required, input.minLength, input.autocomplete]),
      };
    }, html);
    if (!["index.html", "cadastro.html", "termos.html", "politica-privacidade.html", "pagamento-sucesso.html"].includes(filename)) {
      expect(parity.actual).toEqual(parity.expected);
      expect(parity.forms).toEqual(parity.originalForms);
    } else if (filename === "index.html") {
      await expect(page.getByRole("heading", { name: "Últimas Publicações" })).toBeVisible();
      await expect(page.locator(".mag-publication")).toHaveCount(3);
    }
    await expect(page).toHaveTitle(filename === "pagamento-sucesso.html" ? "Confirmação do pagamento | Comunidade Unidos em Cristo" : parity.title);
    // Load offscreen cards for the complete asset check and full-page capture.
    await page.locator('img[loading="lazy"]').evaluateAll((images) => images.forEach((img) => { img.loading = "eager"; }));
    await expect.poll(() => page.locator("img").evaluateAll((images) =>
      images.every((img) => img.complete && img.naturalWidth > 0),
    )).toBe(true);
    const overflow = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
    expect(overflow.document).toBeLessThanOrEqual(overflow.width + 1);
    const localLinks = await page.locator('a[href^="/"]').evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    for (const href of localLinks) {
      if (!href.startsWith("/grupos/") && !href.startsWith("/conteudos/")) expect([...pages, "area-associado.html", "grupos.html", "facilitadores.html", "comunidade-online.html", "assinatura.html", "minha-assinatura.html", "agenda.html", "mural.html", "newsletter.html", "gestao-comunicacao.html"], `Unmapped local route: ${href}`).toContain(href.split("#")[0].slice(1));
    }
    expect(errors).toEqual([]);
    expect(failedLocalResponses).toEqual([]);
    await mkdir(artifactDir, { recursive: true });
    const currentScreenshot = await page.screenshot({ path: fileURLToPath(new URL(`${testInfo.project.name}-${filename}.png`, artifactDir)), fullPage: true });
    if (!["index.html", "cadastro.html", "termos.html", "politica-privacidade.html", "pagamento-sucesso.html"].includes(filename)) {
      // Render the preserved HTML with its own CSS, without exposing the repository.
      const legacy = await context.newPage();
      await legacy.route("**/__legacy/**", async (route) => {
        const resource = new URL(route.request().url()).pathname.slice("/__legacy/".length);
        const allowed = [filename, "css/style.css", "assets/logo/logo.png"];
        if (!allowed.includes(resource)) return route.fulfill({ status: 404, body: "" });
        const contentType = resource.endsWith(".css") ? "text/css" : resource.endsWith(".png") ? "image/png" : "text/html; charset=utf-8";
        return route.fulfill({ body: await readFile(new URL(resource, root)), contentType });
      });
      await legacy.goto(`/__legacy/${filename}`);
      await expect.poll(() => legacy.locator("img").evaluateAll((images) => images.every((img) => img.complete && img.naturalWidth > 0))).toBe(true);
      const originalScreenshot = await legacy.screenshot({ path: fileURLToPath(new URL(`${testInfo.project.name}-original-${filename}.png`, artifactDir)), fullPage: true });
      expect(currentScreenshot.equals(originalScreenshot), "Rendered React page must preserve the original appearance").toBe(true);
      await legacy.close();
    }
  });
}

test("root URL and unknown route", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Unidos em Cristo");
  await page.goto("/pagina-inexistente");
  await expect(page.getByRole("heading", { name: "Página não encontrada" })).toBeVisible();
  await page.getByRole("link", { name: "Voltar ao início" }).click();
  await expect(page.locator("h1")).toContainText("Unidos em Cristo");
});

test("navigation stays in React and restores anchors and focus", async ({ page }, testInfo) => {
  await page.goto("/index.html#associacao");
  await expect(page.locator("#associacao")).toBeFocused();
  const directAnchor = await page.locator("#associacao").boundingBox();
  expect(directAnchor.y).toBeGreaterThanOrEqual(60);
  expect(directAnchor.y).toBeLessThan(page.viewportSize().height);
  await page.evaluate(() => { window.__navigationMarker = "same-document"; });
  await page.locator(".footer-links").getByRole("link", { name: "Privacidade", exact: true }).click();
  await expect(page).toHaveURL(/politica-privacidade\.html$/);
  await expect(page.locator("main")).toBeFocused();
  expect(await page.evaluate(() => window.__navigationMarker)).toBe("same-document");
  await page.getByRole("link", { name: "Voltar ao início" }).click();
  await expect(page).toHaveURL(/index\.html#inicio$/);
  await expect(page.locator("#inicio")).toBeFocused();
  await page.locator(".hero-actions").getByRole("link").click();
  await expect(page).toHaveURL(/#associacao$/);
  await expect(page.locator("#associacao")).toBeFocused();
  const bounds = await page.locator("#associacao").boundingBox();
  expect(bounds.y).toBeGreaterThanOrEqual(60);
  expect(bounds.y).toBeLessThan(page.viewportSize().height);
  await page.goBack();
  await expect(page).toHaveURL(/#inicio$/);
  await expect(page.locator("#inicio")).toBeFocused();
  await page.screenshot({ path: fileURLToPath(new URL(`${testInfo.project.name}-inicio.png`, artifactDir)) });
  await page.locator(".footer-links").getByRole("link", { name: "Contato", exact: true }).click();
  await expect(page.locator("#contato")).toBeFocused();
});

test("mobile menu closes with Escape, selection, outside click and resize", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Abrir menu" });
  const menu = page.getByRole("navigation", { name: "Navegação principal" });
  await expect(menu).toBeHidden();
  await toggle.click();
  await expect(menu).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menu).toBeHidden();
  await expect(toggle).toBeFocused();
  await toggle.click();
  await menu.getByRole("link", { name: "Grupos", exact: true }).click();
  await expect(menu).toBeHidden();
  await expect(page.locator("#como-atuamos")).toBeFocused();
  await expect(page.locator('#main-menu a[href$="#como-atuamos"]')).toHaveAttribute("aria-current", "location");
  await toggle.click();
  await page.locator("#como-atuamos h2").click();
  await expect(menu).toBeHidden();
  await toggle.click();
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(menu).toBeHidden();
});

test("video and contribution buttons do not load unknown services", async ({ page }) => {
  const outbound = [];
  page.on("request", (request) => { if (!request.url().startsWith("http://127.0.0.1")) outbound.push(request.url()); });
  await page.goto("/");
  outbound.length = 0;
  await expect(page.locator("iframe")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "Explore a comunidade online" }).getByRole("link", { name: "Vídeos e Formações" })).toHaveAttribute("href", "/comunidade-online.html");
  await page.getByRole("button", { name: /Assine Agora/ }).click();
  await expect(page).toHaveURL(/assinatura.html$/);
  await expect(page.getByRole("button", { name: /Ir para o pagamento seguro/ })).toBeDisabled();
  await expect(page.getByText(/A contratação ainda não foi ativada/)).toBeVisible();
  expect(outbound).toEqual([]);
});

for (const [filename, submit] of [["recuperar-senha.html", "Enviar instruções"]]) {
  test(`${filename}: native validation and honest form feedback`, async ({ page }) => {
    const apiRequests = [];
    page.on("request", (request) => { if (request.url().includes("/api/")) apiRequests.push(request.url()); });
    await page.goto(`/${filename}`);
    await page.getByRole("button", { name: submit, exact: true }).click();
    await expect(page.locator("input:invalid").first()).toBeFocused();
    await expect(page.locator('[role="status"]')).toBeEmpty();
    for (const input of await page.locator("input").all()) {
      const type = await input.getAttribute("type");
      await input.fill(type === "email" ? "teste@example.invalid" : type === "password" ? "SomenteTeste123!" : "Pessoa de teste");
    }
    await page.getByRole("button", { name: submit, exact: true }).click();
    await expect(page.getByRole("status")).toContainText("ainda não está disponível");
    await expect(page).toHaveURL(new RegExp(`${filename.replace(".", "\\.")}$`));
    expect(apiRequests).toEqual([]);
    expect(await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length }))).toEqual({ local: 0, session: 0 });
  });
}

test("cadastro.html: invitation resend validates email and gives private feedback", async ({ page }) => {
  await page.goto("/cadastro.html");
  await expect(page.getByRole("button", { name: "Concluir cadastro", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "Solicitar novo link", exact: true }).click();
  await expect(page.locator("input:invalid")).toBeFocused();
  await page.getByLabel("E-mail do pagamento", { exact: true }).fill("test@example.invalid");
  await page.getByRole("button", { name: "Solicitar novo link", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Se houver uma assinatura válida");
});

test("known social contacts, identity colors and keyboard skip link", async ({ page }) => {
  await page.goto("/");
  const social = page.locator(".social");
  await expect(social.getByRole("link", { name: "Instagram" })).toHaveAttribute("href", "https://www.instagram.com/cuc_unidosemcristo/");
  await expect(social.getByRole("link", { name: "Facebook" })).toHaveAttribute("href", "https://www.facebook.com/ComUnidosEmCristo");
  await expect(social.getByRole("link", { name: "YouTube" })).toHaveAttribute("href", "https://www.youtube.com/");
  await expect(social.locator("a")).toHaveCount(3);
  await expect(social.locator("svg")).toHaveCount(3);
  expect(await page.evaluate(() => {
    const style = getComputedStyle(document.documentElement);
    return ["--red", "--gold", "--paper"].map((name) => style.getPropertyValue(name).trim());
  })).toEqual(["#b91f1f", "#a68b4e", "#fffdf8"]);
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Pular para o conteúdo" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});
