import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = new URL(process.env.CUC_API_TARGET ?? "http://127.0.0.1:8000");
if (!["127.0.0.1", "localhost"].includes(apiTarget.hostname)) {
  throw new Error("O proxy de desenvolvimento aceita somente uma API local.");
}

export default defineConfig({
  plugins: [react()],
  server: {
    fs: { allow: [".", "../css", "../assets"] },
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/media": { target: apiTarget.origin },
      "/api": {
        target: apiTarget.origin,
        changeOrigin: true,
      },
    },
  },
});
