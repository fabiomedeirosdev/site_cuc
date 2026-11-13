import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_BILLING_E2E !== "1") throw new Error("Execute manage.py test apps.billing.browser_tests para usar dados temporários.");

export default defineConfig({
  ...base,
  timeout: 45000,
  testMatch: "billing.spec.js",
  outputDir: "../.local/phase6/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/phase6/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5177", trace: "off" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5177", url: "http://127.0.0.1:5177", reuseExistingServer: false, timeout: 30000 },
});
