import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

if (process.env.CUC_PROFILES_E2E !== "1") throw new Error("Execute manage.py test apps.accounts.profile_browser_tests para usar o banco temporário.");

export default defineConfig({
  ...base,
  testMatch: "profiles.spec.js",
  timeout: 60000,
  maxFailures: 1,
  outputDir: "../.local/profiles/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/profiles/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5184" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5184", url: "http://127.0.0.1:5184", reuseExistingServer: false, timeout: 30000 },
});
