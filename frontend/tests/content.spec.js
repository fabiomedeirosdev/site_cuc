import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "www.youtube-nocookie.com") return route.fulfill({ contentType: "text/html", body: "<!doctype html><html><body style='background:#201714;color:white'>Player YouTube simulado para teste offline</body></html>" });
    return url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
});

async function login(page, project, role) {
  await page.goto("/meus-conteudos.html");
  await expect(page).toHaveURL(/login.html$/);
  await page.getByLabel("E-mail", { exact: true }).fill(`${project}.${role}@example.invalid`);
  await page.getByLabel("Senha", { exact: true }).fill("LocalContentTest!8-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/meus-conteudos.html$/);
}

for (const role of ["reader"]) {
  test(`${role} cannot create content or upload covers`, async ({ page }, info) => {
    await login(page, info.project.name, role);
    await expect(page.getByText(/criação de conteúdo exige/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Criar conteúdo/ })).toHaveCount(0);
    await page.goto("/editor/novo");
    await expect(page.getByText(/Somente facilitadores e coordenadores vinculados/)).toBeVisible();
    expect((await page.request.get("/api/editorial/author-groups")).status()).toBe(200);
    expect((await (await page.request.get("/api/editorial/author-groups")).json()).length).toBe(0);
  });
}

test("columnist creates article with photo and embedded video, edits and deletes it", async ({ page }, info) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await login(page, info.project.name, "columnist");
  await page.getByRole("link", { name: /Criar conteúdo/ }).click();
  await page.getByLabel("Título", { exact: true }).fill(`Uma caminhada de fé ${info.project.name}`);
  await page.getByLabel("Resumo", { exact: true }).fill("Um resumo para a comunidade.");
  await page.getByLabel("Texto do conteúdo", { exact: true }).fill("## Esperança\n\nUm texto com **fé** e comunhão.\n\n<script>window.unsafeArticle = true</script>");
  await page.getByRole("button", { name: "Prévia", exact: true }).click();
  await expect(page.locator(".content-preview h2")).toHaveText("Esperança");
  await expect(page.locator(".content-preview strong")).toHaveText("fé");
  expect(await page.evaluate(() => window.unsafeArticle)).toBeUndefined();
  await page.getByLabel("Escolher foto", { exact: true }).setInputFiles(process.env.CUC_E2E_COVER);
  await expect(page.locator(".content-cover-preview")).toBeVisible();
  await page.getByLabel("Descrição da foto", { exact: true }).fill("Uma paisagem dourada de teste");
  await page.getByLabel("Link do vídeo do YouTube", { exact: true }).fill("https://youtu.be/abcdefghijk");
  await expect(page.locator(".content-video iframe")).toHaveAttribute("src", "https://www.youtube-nocookie.com/embed/abcdefghijk");
  await page.getByRole("button", { name: "Publicar", exact: true }).click();
  await expect(page).toHaveURL(/\/editor\/\d+$/);
  await expect(page.getByRole("link", { name: "Ver publicação" })).toBeVisible();
  await page.getByRole("link", { name: "Ver publicação" }).click();
  await expect(page.locator(".content-prose strong")).toHaveText("fé");
  await expect(page.locator(".content-video iframe")).toBeVisible();
  await expect(page.locator(".content-reading-cover")).toBeVisible();
  expect(await page.evaluate(() => window.unsafeArticle)).toBeUndefined();
  await page.goto("/");
  await expect(page.locator(".mag-publication").filter({ hasText: `Uma caminhada de fé ${info.project.name}` })).toBeVisible();
  const social = page.locator(".mag-social");
  await expect(social.locator("a")).toHaveCount(3);
  await expect(social.locator("svg")).toHaveCount(3);
  await page.goto("/meus-conteudos.html");
  await page.getByRole("link", { name: "Editar", exact: true }).click();
  await page.getByLabel("Título", { exact: true }).fill(`Título atualizado ${info.project.name}`);
  await page.getByRole("button", { name: "Salvar alterações", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Conteúdo publicado");
  await mkdir("../.local/phase5/screenshots", { recursive: true });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({ path: `../.local/phase5/screenshots/${info.project.name}-editor.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole("link", { name: /Meus conteúdos/ }).click();
  await page.getByRole("button", { name: "Excluir", exact: true }).click();
  await page.getByRole("button", { name: "Confirmar exclusão", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Conteúdo excluído" })).toBeVisible();
  await page.goto("/");
  await expect(page.locator(".mag-publication")).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("coordinator edits and deletes facilitator content preserving authorship", async ({ page, context }, info) => {
  const project = info.project.name;
  await login(page, project, "columnist");
  const groups = await (await page.request.get("/api/editorial/author-groups")).json();
  const csrf = await (await page.request.get("/api/auth/csrf")).json();
  const created = await page.request.post("/api/editorial/articles", { headers: { "X-CSRFToken": csrf.csrf_token }, data: { group: groups[0].id, title: `Para revisão ${project}`, body: "Texto do facilitador" } });
  expect(created.status()).toBe(201);
  const article = await created.json();
  await context.clearCookies();
  await login(page, project, "coordinator");
  await expect(page.getByRole("heading", { name: "Conteúdos dos Grupos", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Editar", exact: true }).click();
  await page.getByLabel("Título", { exact: true }).fill(`Revisado ${project}`);
  await page.getByRole("button", { name: "Salvar rascunho", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Rascunho salvo");
  const edited = await (await page.request.get(`/api/editorial/articles/${article.id}`)).json();
  expect(edited.author_name).toBe(article.author_name);
  expect(edited.title).toBe(`Revisado ${project}`);
  await page.getByRole("link", { name: /Meus conteúdos/ }).click();
  await page.getByRole("button", { name: "Excluir", exact: true }).click();
  await page.getByRole("button", { name: "Confirmar exclusão", exact: true }).click();
  await expect(page.getByRole("status").filter({ hasText: "Conteúdo excluído" })).toBeVisible();
});
