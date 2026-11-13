import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_EDITORIAL_E2E !== "1") {
  throw new Error("Execute manage.py test apps.editorial.browser_tests para usar o banco temporário.");
}

export default defineConfig({
  ...base,
  testMatch: "editorial.spec.js",
  outputDir: "../.local/phase4/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/phase4/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5175" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5175", url: "http://127.0.0.1:5175", reuseExistingServer: false, timeout: 30000 },
});
