import { defineConfig } from "@playwright/test";
import base from "./playwright.config.js";

export default defineConfig({
  ...base,
  testMatch: ["home.spec.js", "community-improvements.spec.js", "notifications.spec.js"],
  outputDir: "../.local/community/browser-results",
  reporter: [["list"]],
  use: { ...base.use, baseURL: "http://127.0.0.1:5187" },
  webServer: { command: "npm run dev -- --host 127.0.0.1 --port 5187", url: "http://127.0.0.1:5187", reuseExistingServer: false, timeout: 30000 },
});
