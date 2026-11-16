import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const article = { id: 701, title: "Nossa caminhada de fé", excerpt: "Uma reflexão da comunidade.", group_name: "Formação", author_name: "Facilitador", cover_url: null, cover_alt: "Bíblia", status: "published", is_featured: false, featured_position: 0, updated_at: "2026-11-12T12:00:00Z", published_at: "2026-11-12T12:00:00Z" };
const user = { id: 1, display_name: "Administração CUC", email: "admin@example.invalid", roles: ["administrator"], can_access_panel: true, can_manage_editorial_groups: true, can_manage_communications: true, capabilities: { create_content: true } };
const pageOf = (results) => ({ count: results.length, next: null, previous: null, results });

async function setup(context, role = "administrator") {
  const state = { article: { ...article }, active: true, teamLists: 0, teamDetails: [], created: null,
    member: { id: 2, display_name: "Associado de teste", email: "reader@example.invalid", first_name: "Associado", last_name: "de teste", biography: "Uma apresentação", website: "", video_url: "", role: "subscriber", community_role: "", position: 0,
      memberships: [], available_groups: [{ id: 1, name: "Formação", is_active: true }, { id: 2, name: "Vida", is_active: true }] } };
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
    else if (url.pathname === "/api/management/users") data = pageOf([{ id: 2, name: state.member.display_name, email: state.member.email, can_edit: true, can_delete: true, is_active: state.active, access_protected: false, joined_at: "2026-11-01T12:00:00Z" }]);
    else if (url.pathname === "/api/management/team") {
      if (request.method() === "POST") { state.created = request.postDataJSON(); data = { ...state.member, ...state.created }; }
      else { state.teamLists++; expect(url.searchParams.get("q")).toBeTruthy(); data = pageOf([state.member]); }
    } else if (url.pathname === "/api/management/team/2") {
      if (request.method() === "PATCH") {
        expect(request.headers()["x-csrftoken"]).toBe("browser-test");
        state.member = { ...state.member, ...request.postDataJSON(), community_role: request.postDataJSON().role };
      } else state.teamDetails.push(2);
      data = state.member;
    }
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

test("equipes mantém cadastro e busca sem abrir formulários de todos os membros", async ({ page, context }) => {
  const state = await setup(context);
  await page.goto("/gestao-grupos.html");
  await expect(page.getByRole("button", { name: "Adicionar integrante", exact: true })).toBeVisible();
  await expect(page.getByLabel("Nome do novo membro", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Senha inicial para novo acesso", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Salvar membro" })).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: "Biografia", exact: true })).toHaveCount(0);
  expect(state.teamLists).toBe(0);
  await page.getByLabel("Buscar membro", { exact: true }).fill("Associado");
  await page.locator("form").filter({ has: page.getByLabel("Buscar membro", { exact: true }) }).getByRole("button", { name: "Buscar", exact: true }).click();
  const results = page.getByRole("list", { name: "Resultados da busca de membros" });
  await expect(results).toContainText("Associado de teste");
  await expect(results.getByRole("textbox")).toHaveCount(0);
  await expect(results.getByRole("link", { name: "Ver cadastro" })).toHaveAttribute("href", "/painel/usuarios/2/editar");
  await page.getByLabel("Buscar membro", { exact: true }).fill("");
  await page.locator("form").filter({ has: page.getByLabel("Buscar membro", { exact: true }) }).getByRole("button", { name: "Buscar", exact: true }).click();
  await expect(results).toHaveCount(0);
  expect(state.teamLists).toBe(1);
  const createForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Adicionar integrante", exact: true }) });
  await createForm.getByLabel("E-mail", { exact: true }).fill("new@example.invalid");
  await createForm.getByLabel("Nome do novo membro", { exact: true }).fill("Novo integrante");
  await createForm.getByLabel("Senha inicial para novo acesso", { exact: true }).fill("InitialPass!928");
  await createForm.getByRole("combobox", { name: "Função", exact: true }).selectOption("priest");
  await createForm.getByRole("button", { name: "Adicionar integrante", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Membro atualizado" })).toBeVisible();
  expect(state.created).toMatchObject({ display_name: "Novo integrante", email: "new@example.invalid", role: "priest", group: null, password: "InitialPass!928" });
  expect(state.teamLists).toBe(1);
  await noOverflow(page);
});

test("usuários abre e salva somente a pessoa selecionada em edição própria", async ({ page, context }) => {
  const state = await setup(context);
  await page.goto("/painel/usuarios");
  await page.getByRole("link", { name: "Editar dados e função", exact: true }).click();
  await expect(page).toHaveURL(/\/painel\/usuarios\/2\/editar$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Editar usuário");
  await expect(page.getByLabel("Nome de exibição", { exact: true })).toHaveCount(1);
  await expect(page.getByLabel("Nome de exibição", { exact: true })).toHaveValue("Associado de teste");
  await expect(page.getByRole("button", { name: "Adicionar integrante", exact: true })).toHaveCount(0);
  expect(state.teamLists).toBe(0);
  expect(state.teamDetails.length).toBeGreaterThan(0);
  expect(state.teamDetails.every((id) => id === 2)).toBe(true);
  await page.getByLabel("Nome de exibição", { exact: true }).fill("Nome corrigido");
  await page.getByRole("combobox", { name: "Função geral", exact: true }).selectOption("administration");
  await page.getByRole("button", { name: "Salvar alterações", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Dados e função atualizados" })).toBeVisible();
  expect(state.member.display_name).toBe("Nome corrigido");
  expect(state.member.role).toBe("administration");
  await expect(page.getByRole("combobox", { name: "Função geral", exact: true })).toHaveValue("administration");
  expect(state.teamLists).toBe(0);
  await noOverflow(page);
  await page.getByRole("link", { name: "Voltar para Usuários" }).click();
  await expect(page).toHaveURL(/\/painel\/usuarios$/);
  await expect(page.getByRole("table")).toContainText("Nome corrigido");
});

test("grupos na edição do usuário permitem escolher e salvar a função de cada vínculo", async ({ page, context }) => {
  const state = await setup(context);
  state.member.memberships = [{ group: 1, role: "columnist" }];
  await page.goto("/painel/usuarios/2/editar");
  const participation = page.getByRole("group", { name: "Participação nos grupos", exact: true });
  const groupSelects = participation.getByRole("combobox", { name: "Grupo", exact: true });
  const roleSelects = participation.getByRole("combobox", { name: "Função no grupo", exact: true });
  const save = page.getByRole("button", { name: "Salvar alterações", exact: true });
  await expect(groupSelects).toHaveValue("1");
  await expect(roleSelects).toHaveValue("columnist");
  await roleSelects.selectOption("coordinator");
  await participation.getByRole("button", { name: "Adicionar outro grupo" }).click();
  await groupSelects.nth(1).selectOption("2");
  await save.click();
  await expect(groupSelects).toHaveCount(2);
  await expect(roleSelects.first()).toHaveValue("coordinator");
  expect(state.member.memberships).toEqual([{ group: 1, role: "coordinator" }, { group: 2, role: "columnist" }]);
  await page.reload();
  await expect(groupSelects).toHaveCount(2);
  await expect(groupSelects.nth(1)).toHaveValue("2");
  await expect(roleSelects.nth(1)).toHaveValue("columnist");
  await participation.getByRole("button", { name: "Remover grupo", exact: true }).first().click();
  await save.click();
  await expect(groupSelects).toHaveCount(1);
  await expect(groupSelects).toHaveValue("2");
  expect(state.member.memberships).toEqual([{ group: 2, role: "columnist" }]);
  expect(state.teamLists).toBe(0);
  await noOverflow(page);
});

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
