import { test, expect } from "@playwright/test";

const pageOf = (results) => ({ count: results.length, results, next: null, previous: null });

test("membros sem grupo, ordem manual e delegação independente", async ({ page, context }) => {
  let delegate = { facilitator_id: 7, can_edit_agenda: true, can_edit_mural: false };
  const writes = [];
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await context.route("**/*", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.hostname !== "127.0.0.1") return route.abort();
    if (!url.pathname.startsWith("/api/")) return route.continue();
    let data = pageOf([]);
    if (url.pathname === "/api/auth/me") data = { id: 1, display_name: "Desenvolvedor", roles: ["administrator"], can_access_panel: true, can_manage_editorial_groups: true, can_order_members: true, can_manage_communications: true, can_delegate_communications: true, communication_sections: ["events", "notices", "campaigns"] };
    if (url.pathname === "/api/auth/csrf") data = { csrf_token: "browser-test" };
    if (url.pathname === "/api/editorial/groups") data = { is_administrator: true, groups: [] };
    if (url.pathname === "/api/management/team") {
      if (request.method() === "POST") { writes.push(request.postDataJSON()); data = { id: 7 }; }
      else data = pageOf([{ id: 7, display_name: "Facilitador", email: "helper@example.invalid", community_role: "columnist", position: 5 }]);
    }
    if (url.pathname === "/api/management/team/7") { writes.push(request.postDataJSON()); data = { id: 7 }; }
    if (url.pathname === "/api/communications/delegation") {
      if (request.method() === "PUT") { writes.push(request.postDataJSON()); delegate = { facilitator_id: 7, ...request.postDataJSON() }; }
      data = { can_delegate: true, candidates: [{ id: 7, name: "Facilitador" }], delegations: [delegate] };
    }
    return route.fulfill({ json: data });
  });
  await page.goto("/gestao-grupos.html");
  await expect(page.getByRole("heading", { name: "Equipes e permissões", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Criar novo grupo|Editar grupos e fotos/ })).toHaveCount(0);
  await page.getByLabel("E-mail", { exact: true }).fill("founder@example.invalid");
  await page.getByRole("combobox", { name: "Grupo", exact: true }).selectOption("");
  await page.getByRole("combobox", { name: "Função", exact: true }).selectOption("founder");
  await page.getByRole("button", { name: "Adicionar integrante" }).click();
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0]).toEqual({ email: "founder@example.invalid", role: "founder", group: null });
  await expect(page.getByLabel("Ordem de exibição")).toBeVisible();
  await page.getByLabel("Ordem de exibição").fill("9");
  await page.getByRole("button", { name: "Salvar membro" }).click();
  await expect.poll(() => writes.length).toBe(2);
  expect(writes[1]).toEqual({ role: "columnist", position: 9 });
  await page.goto("/gestao-comunicacao.html");
  await page.getByRole("button", { name: "Equipe", exact: true }).click();
  await page.getByRole("combobox", { name: "Facilitador", exact: true }).selectOption("7");
  await expect(page.getByLabel("Pode editar a agenda")).toBeChecked();
  await expect(page.getByLabel("Pode editar o mural")).not.toBeChecked();
  await page.getByLabel("Pode editar a agenda").uncheck();
  await page.getByLabel("Pode editar o mural").check();
  await page.getByRole("button", { name: "Salvar permissões" }).click();
  await expect.poll(() => writes.length).toBe(3);
  expect(writes[2]).toEqual({ facilitator: 7, can_edit_agenda: false, can_edit_mural: true });
  expect(errors).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
