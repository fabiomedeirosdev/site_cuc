import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_E2E !== "1") {
  throw new Error("Execute a integração pelo Django: manage.py test apps.accounts.browser_tests. Ela prepara e remove o banco de teste.");
}

export default defineConfig({
  ...base,
  testMatch: "auth.spec.js",
  outputDir: "../.local/phase3/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/phase3/report", open: "never" }]],
});
