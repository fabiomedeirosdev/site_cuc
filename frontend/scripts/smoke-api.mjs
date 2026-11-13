import assert from "node:assert/strict";
import { createServer } from "vite";
import { createApiClient } from "../src/api-client.js";

// Django and PostgreSQL must already be running. This server is owned by the test.
const vite = await createServer({ server: { host: "127.0.0.1", port: 0, strictPort: false } });
try {
  await vite.listen();
  const { port } = vite.httpServer.address();
  const origin = `http://127.0.0.1:${port}`;
  const api = createApiClient({ baseUrl: origin });
  const options = () => ({ signal: AbortSignal.timeout(10000) });
  assert.equal((await api.getHealth(options())).status, "ok");
  console.log("PASS React client -> Vite proxy -> Django /api/health");
  assert.deepEqual(await api.getReadiness(options()), { status: "ok", database: "ok" });
  console.log("PASS React client -> Vite proxy -> Django -> PostgreSQL /api/ready");
  const response = await fetch(origin, options());
  assert.equal(response.status, 200);
  assert.match(await response.text(), /\/src\/main.jsx/);
  console.log("PASS Vite serves the React entry point");
} finally {
  await vite.close();
}
