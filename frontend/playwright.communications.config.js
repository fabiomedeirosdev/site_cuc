import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";
if (process.env.CUC_COMMUNICATIONS_E2E !== "1") throw new Error("Execute manage.py test apps.communications.browser_tests para usar o banco temporário.");
export default defineConfig({
  ...base,
  timeout: 45000,
  maxFailures: 1,
  testMatch: "communications.spec.js",
  outputDir: "../.local/phase7/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/phase7/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5178", trace: "off" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5178", url: "http://127.0.0.1:5178", reuseExistingServer: false, timeout: 30000 },
});
