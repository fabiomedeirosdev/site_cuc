import { defineConfig } from "@playwright/test";
import base from "./playwright.management.config.js";

if (process.env.CUC_MANAGEMENT_LIVE !== "1") throw new Error("Execute manage.py test apps.core.management_browser_tests para usar o banco temporário.");

export default defineConfig({
  ...base,
  testMatch: "management-live.spec.js",
  outputDir: "../.local/management-live/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/management-live/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5181" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5181", url: "http://127.0.0.1:5181", reuseExistingServer: false, timeout: 30000 },
});
