import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const article = { id: 701, title: "Nossa caminhada de fé", excerpt: "Uma reflexão da comunidade.", group_name: "Formação", author_name: "Facilitador", cover_url: null, cover_alt: "Bíblia", status: "published", is_featured: false, featured_position: 0, updated_at: "2026-11-12T12:00:00Z", published_at: "2026-11-12T12:00:00Z" };
const user = { id: 1, display_name: "Administração CUC", email: "admin@example.invalid", roles: ["administrator"], can_access_panel: true, can_manage_editorial_groups: true, can_manage_communications: true, capabilities: { create_content: true } };
const pageOf = (results) => ({ count: results.length, next: null, previous: null, results });

async function setup(context, role = "administrator") {
  const state = { article: { ...article }, active: true };
  const account = role === "administrator" ? user : { ...user, roles: [role], can_access_panel: role !== "subscriber", can_manage_editorial_groups: role === "coordinator", can_manage_communications: role === "coordinator", capabilities: { create_content: role !== "subscriber" } };
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
  await context.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    let data = {};
    if (url.pathname === "/api/auth/me") data = account;
    else if (url.pathname === "/api/auth/csrf") data = { csrf_token: "browser-test" };
    else if (url.pathname === "/api/management/dashboard") data = { scope: "Todo o site", totals: { contents: 1, published: 1, drafts: 0, featured: Number(state.article.is_featured), users: 2 }, activity: ["06", "07", "08", "09", "10", "11"].map((month, i) => ({ month: `${month}/2026`, total: i === 5 ? 1 : 0 })), recent: [state.article] };
    else if (url.pathname === "/api/management/highlights") data = pageOf([state.article]);
    else if (url.pathname === "/api/management/highlights/701") {
      expect(request.method()).toBe("PATCH");
      expect(request.headers()["x-csrftoken"]).toBe("browser-test");
      state.article = { ...state.article, ...request.postDataJSON(), updated_at: new Date().toISOString() };
      data = state.article;
    } else if (url.pathname === "/api/articles") data = pageOf(url.searchParams.has("featured") ? state.article.is_featured ? [state.article] : [] : [state.article]);
    else if (url.pathname === "/api/management/users") data = pageOf([{ id: 2, name: "Associado de teste", email: "reader@example.invalid", is_active: state.active, access_protected: false, joined_at: "2026-11-01T12:00:00Z" }]);
    else if (url.pathname === "/api/management/users/2") { state.active = request.postDataJSON().is_active; data = { id: 2, is_active: state.active }; }
    else if (url.pathname === "/api/management/groups") data = [{ id: 1, name: "Formação", slug: "formacao", description: "Grupo de formação", cover: "bible", is_active: true, position: 0 }];
    else if (url.pathname === "/api/management/groups/1") data = { id: 1, name: "Formação", slug: "formacao", description: "Apresentação atualizada pelo painel.", cover: "bible", cover_url: null, cover_alt: "", is_active: true, position: 0 };
    else if (url.pathname === "/api/editorial/groups") data = { is_administrator: true, groups: [] };
    else if (url.pathname === "/api/editorial/author-groups") data = [{ id: 1, name: "Formação", slug: "formacao" }];
    else if (url.pathname === "/api/editorial/articles") data = pageOf([state.article]);
    else if (url.pathname === "/api/communications/weekly") data = { weekly_enabled: false, weekday: 0, hour: 9, subject: "Novidades", introduction: "Bem-vindo" };
    else data = pageOf([]);
    await route.fulfill({ json: data });
  });
  return state;
}

async function noOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

test("painel, seleção de destaque e publicação no carrossel", async ({ page, context }, testInfo) => {
  const state = await setup(context);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/painel");
  await expect(page.getByRole("heading", { name: "Visão geral" })).toBeVisible();
  await expect(page.getByRole("img", { name: /06\/2026: 0 publicações/ })).toBeVisible();
  await expect(page.getByRole("table")).toContainText(article.title);
  await noOverflow(page);
  await mkdir("../.local/management/screenshots", { recursive: true });
  await page.screenshot({ path: `../.local/management/screenshots/${testInfo.project.name}-painel.png`, fullPage: true });
  await page.getByRole("link", { name: "Destaques do site" }).click();
  await page.getByRole("checkbox", { name: "Exibir em destaque na página inicial" }).check();
  await page.getByRole("spinbutton", { name: "Ordem no carrossel" }).fill("2");
  await page.getByRole("button", { name: "Salvar destaque" }).click();
  await expect(page.getByRole("status").filter({ hasText: "atualizado na página inicial" })).toBeVisible();
  expect(state.article.is_featured).toBe(true);
  expect(state.article.featured_position).toBe(2);
  await noOverflow(page);
  await page.getByRole("link", { name: "Ver página inicial" }).click();
  await expect(page.locator(".mag-feature h2")).toHaveText(article.title);
  await expect(page.locator(".mag-feature").getByRole("link", { name: "Ler conteúdo" })).toHaveAttribute("href", "/conteudos/701");
  await page.goto("/painel/destaques");
  await page.getByRole("checkbox", { name: "Exibir em destaque na página inicial" }).uncheck();
  await page.getByRole("button", { name: "Salvar destaque" }).click();
  await expect(page.getByRole("status").filter({ hasText: "atualizado na página inicial" })).toBeVisible();
  await page.goto("/index.html");
  await expect(page.locator(".mag-feature h2")).toContainText("A Missão do Cristão");
  expect(errors).toEqual([]);
});

test("telas de gestão compartilham a identidade e controles funcionam", async ({ page, context }) => {
  const state = await setup(context);
  for (const [path, title] of [["/painel/usuarios", "Usuários"], ["/painel/assinaturas", "Assinaturas"], ["/painel/atendimentos", "Atendimentos"], ["/painel/grupos", "Páginas dos grupos"], ["/meus-conteudos.html", "Conteúdos dos Grupos"], ["/editor/novo", "Criar Conteúdo"], ["/gestao-grupos.html", "Gestão dos Grupos"], ["/gestao-comunicacao.html", "Agenda, Mural e Newsletter"]]) {
    await page.goto(path);
    await expect(page.getByRole("navigation", { name: "Administração", exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(title);
    await noOverflow(page);
  }
  await page.goto("/painel/usuarios");
  await page.getByRole("button", { name: "Suspender acesso" }).click();
  await page.getByRole("button", { name: "Confirmar", exact: true }).click();
  await expect(page.getByText("Suspenso", { exact: true })).toBeVisible();
  expect(state.active).toBe(false);
  await page.goto("/painel/grupos");
  await page.getByRole("textbox", { name: "Apresentação", exact: true }).fill("Apresentação atualizada pelo painel.");
  await page.getByRole("button", { name: "Salvar página do grupo" }).click();
  await expect(page.getByRole("status").filter({ hasText: "atualizada" })).toBeVisible();
});

test("coordenador vê destaques e assinante recebe acesso restrito", async ({ page, context }) => {
  await setup(context, "coordinator");
  await page.goto("/painel");
  await expect(page.getByRole("link", { name: "Destaques do site" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Usuários", exact: true })).toHaveCount(0);
  await page.goto("/painel/usuarios");
  await expect(page.getByRole("alert")).toHaveText("Esta página é exclusiva da administração.");
  await context.unrouteAll({ behavior: "wait" });
  await setup(context, "subscriber");
  await page.goto("/painel");
  await expect(page.getByRole("heading", { name: "Acesso restrito" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Administração", exact: true })).toHaveCount(0);
});
