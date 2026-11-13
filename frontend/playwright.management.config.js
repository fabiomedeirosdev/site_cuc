import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

export default defineConfig({
  ...base,
  timeout: 60000,
  testMatch: "management.spec.js",
  outputDir: "../.local/management/test-results",
  reporter: [["list"], ["html", { outputFolder: "../.local/management/report", open: "never" }]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5180" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5180", url: "http://127.0.0.1:5180", reuseExistingServer: false, timeout: 30000 },
});
