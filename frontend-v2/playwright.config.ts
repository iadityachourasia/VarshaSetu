import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  // One worker: the specs share one local backend and one Next server, and two workers made different map- and district-heavy specs time out on each run (all 104 pass serially).
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: "http://127.0.0.1:3100", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], channel: "chrome", viewport: { width: 1440, height: 900 } } }],
  webServer: [
    { command: ".\\.venv\\Scripts\\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000", cwd: "..", url: "http://127.0.0.1:8000/api/science/status", reuseExistingServer: true, timeout: 120_000,
      // The coverage endpoint is closed unless the page is shown; the variable that builds the frontend with the page also opens the endpoint.
      env: { SHOW_COVERAGE_API: process.env.NEXT_PUBLIC_SHOW_COMPLIANCE_PAGE === "1" ? "1" : "0" } },
    { command: "node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3100", url: "http://127.0.0.1:3100", reuseExistingServer: true, timeout: 120_000 },
  ],
});
