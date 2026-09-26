import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } } }],
  webServer: [
    { command: ".\\.venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", cwd: "..", url: "http://127.0.0.1:8000/api/science/status", reuseExistingServer: true, timeout: 120_000 },
    { command: "node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100", reuseExistingServer: true, timeout: 120_000 },
  ],
});
