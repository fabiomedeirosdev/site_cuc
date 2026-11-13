import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_CONTENT_E2E !== "1") throw new Error("Execute manage.py test apps.content.browser_tests para usar o banco temporário.");

export default defineConfig({
  ...base,
  timeout: 45000,
  testMatch: "content.spec.js",
  outputDir: "../.local/phase5/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/phase5/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5176" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5176", url: "http://127.0.0.1:5176", reuseExistingServer: false, timeout: 30000 },
});
