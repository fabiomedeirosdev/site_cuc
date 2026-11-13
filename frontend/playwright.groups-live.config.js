import { defineConfig } from "@playwright/test";
import base from "./playwright.management.config.js";

if (process.env.CUC_GROUPS_LIVE !== "1") throw new Error("Execute manage.py test apps.editorial.group_browser_tests para usar o banco temporário.");

export default defineConfig({
  ...base,
  testMatch: "groups-live.spec.js",
  outputDir: "../.local/groups-live/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/groups-live/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5182" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5182", url: "http://127.0.0.1:5182", reuseExistingServer: false, timeout: 30000 },
});
