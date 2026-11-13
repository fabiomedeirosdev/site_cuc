import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_FOUNDERS_E2E !== "1") throw new Error("Execute manage.py test apps.core.founders_browser_tests para usar o banco temporário.");

export default defineConfig({
  ...base,
  testMatch: "founders.spec.js",
  timeout: 60000,
  maxFailures: 1,
  outputDir: "../.local/founders/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/founders/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5185" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5185", url: "http://127.0.0.1:5185", reuseExistingServer: false, timeout: 30000 },
});
