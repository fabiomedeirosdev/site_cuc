import { test, expect } from "@playwright/test";

async function setup(context, team) {
  let read = false;
  let responded = false;
  const now = new Date().toISOString();
  await context.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname !== "127.0.0.1") return route.abort();
    if (!url.pathname.startsWith("/api/")) return route.continue();
    let data = { count: 0, results: [], next: null, previous: null };
    if (url.pathname === "/api/auth/me") data = { id: 1, display_name: "Pessoa de teste", roles: team ? ["columnist"] : ["subscriber"], can_access_panel: team, can_handle_inbox: team, capabilities: {} };
    else if (url.pathname === "/api/auth/csrf") data = { csrf_token: "notification-test" };
    else if (url.pathname === "/api/newsletter/preference") data = { opted_in: false };
    else if (url.pathname === "/api/notifications") {
      if (request.method() === "POST") { expect(request.headers()["x-csrftoken"]).toBe("notification-test"); read = true; }
      data = { as_of: now, unread_count: read ? 0 : 1, pending_count: team && !responded ? 1 : 0, updates: [{ id: "article-1", kind: "article", label: "Conteúdo", title: "Nova reflexão publicada", url: "/conteudos/1", at: now, unread: !read }], pending: team && !responded ? [{ id: "email-1", kind: "email", label: "E-mail · Resposta pendente", title: "Preciso conversar com a comunidade", url: "/painel/mensagens?mensagem=1", at: now, pending: true, unread: true }] : [] };
    } else if (url.pathname === "/api/inbox") data = { count: responded && url.searchParams.get("status") !== "all" ? 0 : 1, results: responded && url.searchParams.get("status") !== "all" ? [] : [{ id: 1, subject: "Preciso conversar com a comunidade", sender: "outside@example.invalid", received_at: now, responded_at: responded ? now : null }], next: null, previous: null, webmail_url: "https://webmail.example.invalid" };
    else if (url.pathname === "/api/inbox/1") {
      if (request.method() === "PATCH") { expect(request.headers()["x-csrftoken"]).toBe("notification-test"); responded = request.postDataJSON().responded; }
      data = { id: 1, subject: "Preciso conversar com a comunidade", sender: "outside@example.invalid", received_at: now, responded_at: responded ? now : null, body: "Preciso de orientação. <script>Mensagem sem execução.</script>" };
    }
    await route.fulfill({ json: data });
  });
}

test("assinante: dropdown, marcar novidades como lidas, Escape e clique fora", async ({ page, context }, info) => {
  await setup(context, false);
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/area-associado.html");
  const bell = page.getByRole("button", { name: /^Notificações/ });
  await expect(bell).toHaveAccessibleName("Notificações: 1 novidades ou atendimentos pendentes");
  await bell.click();
  const dropdown = page.getByRole("region", { name: "Últimas notificações" });
  await expect(dropdown.getByRole("link", { name: /Nova reflexão publicada/ })).toHaveAttribute("href", "/conteudos/1");
  await expect(dropdown.getByText(/Precisa de resposta/)).toHaveCount(0);
  await dropdown.screenshot({ path: info.outputPath("subscriber-notifications.png") });
  await page.getByRole("button", { name: "Marcar como lidas" }).click();
  await expect(bell).toHaveAccessibleName("Notificações");
  await page.keyboard.press("Escape");
  await expect(bell).toHaveAttribute("aria-expanded", "false");
  await expect(bell).toBeFocused();
  await bell.click();
  await page.getByRole("heading", { name: /Olá/ }).click();
  await expect(dropdown).toHaveCount(0);
  await page.reload();
  await expect(bell).toHaveAccessibleName("Notificações");
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});

test("equipe: e-mail continua pendente após ler novidades e pode ser atendido", async ({ page, context }, info) => {
  await setup(context, true);
  await page.goto("/area-associado.html");
  let bell = page.getByRole("button", { name: /^Notificações/ });
  await expect(bell).toHaveAccessibleName("Notificações: 2 novidades ou atendimentos pendentes");
  await bell.click();
  await page.getByRole("button", { name: "Marcar como lidas" }).click();
  await expect(bell).toHaveAccessibleName("Notificações: 1 novidades ou atendimentos pendentes");
  await page.getByRole("region", { name: "Últimas notificações" }).screenshot({ path: info.outputPath("team-notifications.png") });
  await page.getByRole("link", { name: /Preciso conversar com a comunidade/ }).click();
  await expect(page).toHaveURL(/painel\/mensagens\?mensagem=1$/);
  await expect(page.getByRole("heading", { name: "Mensagens recebidas", exact: true })).toBeVisible();
  await expect(page.locator(".inbox-body")).toContainText("<script>");
  await expect(page.locator(".inbox-detail script")).toHaveCount(0);
  await page.getByRole("button", { name: "Marcar como respondida" }).click();
  await expect(page.getByText("Resposta registrada", { exact: true })).toBeVisible();
  bell = page.getByRole("button", { name: /^Notificações/ });
  await expect(bell).toHaveAccessibleName("Notificações");
  await expect(page.getByRole("button", { name: "Reabrir atendimento" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
