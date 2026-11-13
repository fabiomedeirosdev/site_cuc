import { test, expect } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const fixtures = JSON.parse(process.env.CUC_BILLING_FIXTURES || "{}");

test.beforeEach(async ({ context }) => {
  await context.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "www.youtube-nocookie.com") return route.fulfill({ contentType: "text/html", body: "<html><body>Vídeo simulado para teste offline</body></html>" });
    if (url.hostname === "pagamento.pagbank.com.br") return route.fulfill({ contentType: "text/html", body: "<html><body>Checkout simulado: nenhuma cobrança</body></html>" });
    return url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
});

async function login(page, email) {
  await page.getByLabel("E-mail", { exact: true }).fill(email);
  await page.getByLabel("Senha", { exact: true }).fill("BillingTest!81-Password");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
}

test("checkout requires consent and opens only the bank payment URL", async ({ page }) => {
  await page.goto("/assinatura.html");
  await expect(page.getByText("R$ 48,20")).toBeVisible();
  await page.getByRole("button", { name: /Ir para o pagamento seguro/ }).click();
  await expect(page).toHaveURL(/assinatura.html$/);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: /Ir para o pagamento seguro/ }).click();
  await expect(page).toHaveURL("https://pagamento.pagbank.com.br/pagamento?code=TEST-ONLY");
});

test("paid invitation creates account, unlocks video, preserves paid days on cancellation", async ({ page }, info) => {
  const fixture = fixtures[info.project.name];
  await page.goto(`/cadastro.html#convite=${fixture.new.token}`);
  await page.getByLabel("Nome completo").fill("Pessoa de teste");
  await page.getByLabel("Crie uma senha", { exact: true }).fill("BillingTest!81-Password");
  await page.getByLabel("Confirme sua senha", { exact: true }).fill("BillingTest!81-Password");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Concluir cadastro", exact: true }).click();
  await expect(page).toHaveURL(/area-associado.html$/);
  await page.goto(`/conteudos/${fixture.article}`);
  await expect(page.locator(".content-prose")).toContainText("Texto exclusivo para assinantes.");
  await expect(page.locator("iframe")).toBeVisible();
  await page.goto("/area-associado.html");
  await page.getByRole("link", { name: "Gerenciar ou cancelar assinatura", exact: true }).click();
  await expect(page).toHaveURL(/minha-assinatura.html$/);
  await expect(page.getByText("Seu acesso está liberado.", { exact: true })).toBeVisible();
  const validity = await page.locator(".billing-access").innerText();
  await page.getByRole("button", { name: "Cancelar assinatura", exact: true }).click();
  await page.getByRole("button", { name: "Confirmar cancelamento", exact: true }).click();
  await expect(page.getByText("Renovação encerrada.", { exact: false })).toBeVisible();
  await expect.poll(() => page.locator(".billing-access").innerText()).toBe(validity);
  await page.getByText("Arrependimento, reembolso ou privacidade", { exact: true }).click();
  await page.getByLabel("Mensagem", { exact: true }).fill("Solicitação fictícia de teste");
  await page.getByRole("button", { name: "Registrar solicitação", exact: true }).click();
  await expect(page.locator(".billing-requests li")).toContainText("Em atendimento");
  expect((await (await page.request.get("/api/auth/me")).json()).exclusive_content_access).toBe(true);
  await expect(page.getByRole("button", { name: "Cancelar assinatura", exact: true })).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
  await mkdir("../.local/phase6/screenshots", { recursive: true });
  // Full-page captures need the page at the top so sticky/fixed navigation is
  // represented at its normal position rather than at the prior form scroll.
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: "instant" }));
  await page.screenshot({ path: `../.local/phase6/screenshots/${info.project.name}-assinatura.png`, fullPage: true });
});

test("existing account must log in to claim the invitation", async ({ page }, info) => {
  const fixture = fixtures[info.project.name];
  await page.goto(`/cadastro.html#convite=${fixture.existing.token}`);
  await page.getByRole("link", { name: "Entrar e vincular assinatura", exact: true }).click();
  await login(page, fixture.existing.email);
  await expect(page).toHaveURL(/cadastro.html$/);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Vincular assinatura", exact: true }).click();
  await expect(page).toHaveURL(/area-associado.html$/);
  expect((await (await page.request.get("/api/auth/me")).json()).exclusive_content_access).toBe(true);
});

test("expired subscriber stays logged in but cannot read paid text or watch video", async ({ page }, info) => {
  await page.goto("/minha-assinatura.html");
  await expect(page).toHaveURL(/login.html$/);
  await login(page, `${info.project.name}.expired@example.invalid`);
  await expect(page).toHaveURL(/minha-assinatura.html$/);
  await page.goto(`/conteudos/${fixtures[info.project.name].article}`);
  await expect(page.locator(".content-prose")).toHaveCount(0);
  await expect(page.locator("iframe")).toHaveCount(0);
  expect((await (await page.request.get("/api/auth/me")).json()).exclusive_content_access).toBe(false);
});
