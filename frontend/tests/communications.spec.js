import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";
const newsletterFixtures = JSON.parse(process.env.CUC_NEWSLETTER_FIXTURES || "{}");

test("cartaz no mural e newsletter com público exclusivo e imagem na prévia", async ({ page, browser }, info) => {
  await login(page, info.project.name, "coordinator");
  const title = `Cartaz do retiro ${info.project.name}`;
  await page.getByRole("button", { name: "Mural", exact: true }).click();
  const editor = page.locator("#communications-editor");
  await editor.getByRole("textbox", { name: "Título", exact: true }).fill(title);
  await editor.getByRole("textbox", { name: "Texto do aviso", exact: true }).fill("Informações exclusivas do retiro.");
  await editor.getByRole("combobox", { name: "Público do conteúdo", exact: true }).selectOption("members");
  await editor.getByLabel("Escolher imagem de divulgação", { exact: true }).setInputFiles(process.env.CUC_COMMUNICATION_IMAGE);
  await editor.getByRole("textbox", { name: "Descrição da imagem", exact: true }).fill("Cartaz vertical do retiro");
  await editor.getByLabel("Publicar no mural", { exact: true }).check();
  await editor.getByRole("button", { name: "Salvar publicação", exact: true }).click();
  await expect(editor.getByRole("status")).toContainText("Conteúdo salvo");
  const notice = (await (await page.request.get("/api/communications/notices")).json()).results.find((item) => item.title === title);
  expect(notice.is_members_only).toBe(true);
  const guest = await browser.newContext({ baseURL: "http://127.0.0.1:5178", viewport: page.viewportSize() });
  try {
    await guest.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
    const guestPage = await guest.newPage();
    await guestPage.goto("/mural.html");
    const card = guestPage.locator("article").filter({ has: guestPage.getByRole("heading", { name: title, exact: true }) });
    await expect(card).toContainText("Este aviso é exclusivo para assinantes");
    await expect(card.locator("img")).toHaveCount(0);
    expect((await guestPage.request.get(notice.image_url)).status()).toBe(404);
    await login(guestPage, info.project.name, "helper");
    await guestPage.goto("/mural.html");
    await expect(card).toContainText("Informações exclusivas do retiro.");
    await expect(card.getByRole("img", { name: "Cartaz vertical do retiro" })).toBeVisible();
    expect((await guestPage.request.get(notice.image_url)).status()).toBe(200);
  } finally { await guest.close(); }
  await page.getByRole("button", { name: "Newsletter", exact: true }).click();
  await editor.getByRole("textbox", { name: "Assunto da edição", exact: true }).fill(`Convite com cartaz ${info.project.name}`);
  await editor.getByRole("textbox", { name: "Mensagem da edição", exact: true }).fill("Veja nosso cartaz e participe.");
  await editor.getByRole("combobox", { name: "Público do conteúdo", exact: true }).selectOption("members");
  await editor.getByLabel("Escolher imagem de divulgação", { exact: true }).setInputFiles(process.env.CUC_COMMUNICATION_IMAGE);
  await editor.getByRole("textbox", { name: "Descrição da imagem", exact: true }).fill("Cartaz da newsletter");
  await editor.getByRole("button", { name: "Ver prévia do e-mail", exact: true }).click();
  const frame = page.frameLocator('iframe[title="Prévia da newsletter"]');
  await expect(frame.getByRole("img", { name: "Cartaz da newsletter", exact: true })).toHaveAttribute("src", /^data:image\/jpeg;base64,/);
  await expect(frame.getByText("Edição exclusiva para assinantes", { exact: true })).toBeVisible();
  await editor.getByRole("button", { name: "Salvar rascunho", exact: true }).click();
  await expect(editor.getByRole("status")).toContainText("Conteúdo salvo");
  const campaign = (await (await page.request.get("/api/communications/campaigns")).json()).results.find((item) => item.subject === `Convite com cartaz ${info.project.name}`);
  expect(campaign.is_members_only).toBe(true);
  expect(campaign.image_url).toMatch(/\/api\/communication-images\/campaigns\//);
  const weekly = page.locator("section").filter({ has: page.getByRole("heading", { name: "Boletim semanal automático", exact: true }) }).last();
  await weekly.getByRole("combobox", { name: "Público do boletim semanal", exact: true }).selectOption("members");
  await weekly.getByLabel("Escolher imagem de divulgação", { exact: true }).setInputFiles(process.env.CUC_COMMUNICATION_IMAGE);
  await weekly.getByRole("textbox", { name: "Descrição da imagem", exact: true }).fill("Cartaz semanal");
  await weekly.getByRole("button", { name: "Salvar programação semanal", exact: true }).click();
  await expect(weekly.getByRole("status").filter({ hasText: "Programação semanal salva" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await mkdir("../.local/phase7/screenshots", { recursive: true });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: `../.local/phase7/screenshots/${info.project.name}-cartazes.png`, fullPage: true });
});

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
});

async function login(page, project, role) {
  await page.goto("/gestao-comunicacao.html");
  await expect(page).toHaveURL(/login.html$/);
  await page.getByLabel("E-mail", { exact: true }).fill(`${project}.${role}@example.invalid`);
  await page.getByLabel("Senha", { exact: true }).fill("CommunicationsTest!81-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page).toHaveURL(/gestao-comunicacao.html$/);
}

test("coordinator publishes and edits agenda; home and mural update automatically", async ({ page }, info) => {
  await login(page, info.project.name, "coordinator");
  const title = `Encontro de fé ${info.project.name}`;
  await page.getByLabel("Título", { exact: true }).fill(title);
  await page.getByLabel("Descrição do evento", { exact: true }).fill("Encontro de oração e partilha da comunidade.");
  const days = 7 - ["desktop", "tablet", "mobile", "small-mobile"].indexOf(info.project.name);
  await page.getByLabel("Início (Brasília)", { exact: true }).fill(new Date(Date.now() + days * 86400000).toISOString().slice(0, 16));
  await page.getByLabel("Local do evento", { exact: true }).fill("Salão da comunidade");
  await page.getByLabel("Publicar na agenda e no mural", { exact: true }).check();
  await page.getByRole("button", { name: "Salvar publicação", exact: true }).click();
  await expect(page.getByText("Conteúdo salvo.", { exact: true })).toBeVisible();
  const card = page.locator(".communications-list article").filter({ hasText: title });
  await card.getByRole("button", { name: "Editar", exact: true }).click();
  await page.getByLabel("Local do evento", { exact: true }).fill("Capela da comunidade");
  await page.getByRole("combobox", { name: "Público do conteúdo", exact: true }).selectOption("members");
  await page.getByRole("button", { name: "Salvar publicação", exact: true }).click();
  await expect(page.getByText("Conteúdo salvo.", { exact: true })).toBeVisible();
  await page.goto("/");
  await expect(page.locator("#agenda").getByText(title, { exact: true })).toBeVisible();
  await page.goto("/mural.html");
  await expect(page.locator("article").filter({ hasText: title })).toContainText("Capela da comunidade");
  await page.goto("/agenda.html");
  await expect(page.getByRole("heading", { name: title, exact: true })).toBeVisible();
  await expect(page.getByText("Apenas para assinantes", { exact: true }).first()).toBeVisible();
  const guest = await page.context().browser().newContext({ baseURL: "http://127.0.0.1:5178", viewport: page.viewportSize() });
  try {
    await guest.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
    const guestPage = await guest.newPage();
    await guestPage.goto("/agenda.html");
    const reserved = guestPage.locator("article").filter({ hasText: title });
    await expect(reserved).toContainText("Apenas para assinantes");
    await expect(reserved).toContainText("Entre com uma assinatura vigente");
    await expect(reserved).not.toContainText("Capela da comunidade");
    const data = await (await guestPage.request.get("/api/events")).json();
    expect(data.results.find((event) => event.title === title).location).toBeNull();
  } finally { await guest.close(); }
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await mkdir("../.local/phase7/screenshots", { recursive: true });
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: `../.local/phase7/screenshots/${info.project.name}-agenda.png`, fullPage: true });
});

test("coordinator appoints helper; helper updates mural but cannot delegate; revocation is immediate", async ({ page, browser }, info) => {
  await login(page, info.project.name, "coordinator");
  await page.getByRole("button", { name: "Equipe", exact: true }).click();
  await Promise.all([
    page.waitForResponse((response) => response.url().endsWith("/api/communications/delegation") && response.request().method() === "PUT" && response.status() === 200),
    page.getByRole("combobox", { name: "Facilitador autorizado", exact: true }).selectOption({ label: `helper ${info.project.name}` }),
  ]);
  await expect(page.getByText("Responsável atualizado.", { exact: true })).toBeVisible();
  const helperContext = await browser.newContext({ baseURL: "http://127.0.0.1:5178", viewport: page.viewportSize() });
  try {
    await helperContext.route("**/*", (route) => new URL(route.request().url()).hostname === "127.0.0.1" ? route.continue() : route.abort());
    const helperPage = await helperContext.newPage();
    await login(helperPage, info.project.name, "helper");
    await helperPage.getByRole("button", { name: "Mural", exact: true }).click();
    await helperPage.getByLabel("Título", { exact: true }).fill(`Aviso do auxiliar ${info.project.name}`);
    await helperPage.getByLabel("Texto do aviso", { exact: true }).fill("Aviso publicado pela pessoa escolhida.");
    await helperPage.getByLabel("Publicar no mural", { exact: true }).check();
    await helperPage.getByRole("button", { name: "Salvar publicação", exact: true }).click();
    await expect(helperPage.getByText("Conteúdo salvo.", { exact: true })).toBeVisible();
    await helperPage.getByRole("button", { name: "Equipe", exact: true }).click();
    await expect(helperPage.getByText("Essa escolha é feita pelo coordenador.", { exact: true })).toBeVisible();
    await Promise.all([
      page.waitForResponse((response) => response.url().endsWith("/api/communications/delegation") && response.request().method() === "PUT" && response.status() === 200),
      page.getByRole("combobox", { name: "Facilitador autorizado", exact: true }).selectOption(""),
    ]);
    await expect(page.getByText("Responsável atualizado.", { exact: true })).toBeVisible();
    expect((await helperPage.request.get("/api/communications/events")).status()).toBe(403);
    await helperPage.reload();
    await expect(helperPage.getByText(/Somente a coordenação e o facilitador escolhido/)).toBeVisible();
  } finally { await helperContext.close(); }
});

test("newsletter supports safe preview, scheduling, weekly Monday at nine and optional account preference", async ({ page }, info) => {
  await login(page, info.project.name, "coordinator");
  await page.getByRole("button", { name: "Newsletter", exact: true }).click();
  await page.getByLabel("Assunto da edição", { exact: true }).fill(`Nossa semana ${info.project.name}`);
  await page.getByLabel("Mensagem da edição", { exact: true }).fill("Uma mensagem de fé, acolhimento e comunhão.\n<script>window.unsafeNewsletter = true</script>");
  await page.getByRole("button", { name: "Ver prévia do e-mail", exact: true }).click();
  await expect(page.frameLocator('iframe[title="Prévia da newsletter"]').getByRole("heading", { name: `Nossa semana ${info.project.name}`, exact: true })).toBeVisible();
  expect(await page.evaluate(() => window.unsafeNewsletter)).toBeUndefined();
  await page.getByLabel("Agendar para (Brasília)", { exact: true }).fill(new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 16));
  await page.getByRole("button", { name: "Agendar envio", exact: true }).click();
  await expect(page.locator(".communications-list article").filter({ hasText: `Nossa semana ${info.project.name}` }).getByText("Envio agendado", { exact: true })).toBeVisible();
  await expect(page.getByRole("combobox", { name: "Dia da semana", exact: true })).toHaveValue("0");
  await expect(page.getByRole("combobox", { name: "Horário de Brasília", exact: true })).toHaveValue("9");
  await page.getByLabel("Ativar boletim semanal automático", { exact: true }).check();
  await page.getByRole("button", { name: "Salvar programação semanal", exact: true }).click();
  await expect(page.getByText("Programação semanal salva.", { exact: true })).toBeVisible();
  expect((await (await page.request.get("/api/communications/weekly")).json()).delivery_available).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await page.goto("/area-associado.html");
  await page.getByLabel("Quero receber a newsletter semanal", { exact: true }).check();
  await expect(page.getByText(/Recebimento autorizado/)).toBeVisible();
  await page.getByLabel("Quero receber a newsletter semanal", { exact: true }).uncheck();
  await expect(page.getByText(/Recebimento desativado/)).toBeVisible();
});

test("visitor joins free newsletter and confirms email without creating an account", async ({ page }, info) => {
  const fixture = newsletterFixtures[info.project.name];
  await page.goto("/");
  await page.getByRole("textbox", { name: "Seu e-mail", exact: true }).fill(fixture.email);
  await page.getByRole("checkbox", { name: /Quero receber a newsletter semanal/ }).check();
  await page.getByRole("button", { name: "Inscrever-se", exact: true }).click();
  await expect(page.locator(".mag-newsletter").getByRole("status")).toContainText("Solicitação recebida");
  await page.goto(`/newsletter.html#confirmar=${fixture.token}`);
  await page.getByRole("button", { name: "Confirmar recebimento", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Recebimento da newsletter confirmado");
  expect((await page.request.get("/api/auth/me")).status()).toBe(403);
});
