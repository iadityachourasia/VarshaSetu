import { expect, test } from "@playwright/test";
import { BASEMAP_SKIP_REASON, basemapReachable } from "./helpers/online";

// Interface refinements: data-health light, evidence chips, forest plots, locator inset, retryable error state.

test("the header reports the verified data state from the API itself", async ({ page }) => {
  const status = await page.request.get("/api/science/status");
  await page.goto("/observations");
  const light = page.getByTestId("api-health");
  await expect(light).toHaveClass(status.ok() ? /api-health-verified/ : /api-health-(unreachable|integrity)/);
  if (status.ok()) await expect(light).toContainText("Evidence verified");
});

test("the header says so when the API cannot be reached", async ({ page }) => {
  await page.route("**/api/science/status", (route) => route.abort());
  await page.goto("/observations");
  await expect(page.getByTestId("api-health")).toHaveClass(/api-health-unreachable/);
  await expect(page.getByTestId("api-health")).toContainText("API unreachable");
});

test("population rows carry a short chip and keep the full governed label in the document", async ({ page }) => {
  await page.goto("/regimes");
  const row = page.getByTestId("coastal-row-2019");
  await expect(row.locator(".evidence-chip-posthoc")).toContainText("Post-hoc · 2019");
  await expect(row.locator(".evidence-chip")).toHaveAttribute("title", "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
  await expect(row).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
});

test("the forest plots agree with the paired-difference table they restate", async ({ page }) => {
  await page.goto("/verification");
  const forest = page.getByTestId("regime-forest").first();
  await expect(forest).toBeVisible();
  await expect(forest.locator("svg")).toHaveCount(3);
  const table = page.locator("table", { hasText: "Δ CSI [95 % interval]" }).first();
  const clearing = await table.locator("tbody tr td:nth-child(2)").evaluateAll((cells) => cells.filter((cell) => /interval excludes 0/.test(cell.textContent ?? "")).length);
  await expect(forest.locator("svg").first().locator(".forest-excludes")).toHaveCount(clearing);
  await expect(forest.locator("svg").first().locator("title")).toContainText(`${clearing} of`);
});

test("every map carries a whole-India locator with the data domain highlighted", async ({ page }) => {
  test.skip(!(await basemapReachable()), BASEMAP_SKIP_REASON);
  await page.goto("/forecast");
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect(page.locator(".locator-inset")).toHaveCount(3);
  await expect(page.locator(".locator-canvas[data-locator-ready='true']")).toHaveCount(3, { timeout: 30_000 });
  await expect(page.locator(".locator-inset").first()).toHaveAttribute("aria-label", /data domain within India/);
});

test("an error state offers a retry that recovers when the API answers again", async ({ page }) => {
  let failing = true;
  await page.route("**/api/science/evidence/reforecast/overview", (route) => (failing ? route.abort() : route.continue()));
  await page.goto("/verification");
  const panel = page.getByTestId("reforecast-study").or(page.locator(".state-message-error").filter({ hasText: /.+/ })).first();
  await panel.scrollIntoViewIfNeeded();
  const error = page.locator(".state-message-error").filter({ has: page.getByRole("button", { name: "Try again" }) }).first();
  await expect(error).toBeVisible({ timeout: 30_000 });
  failing = false;
  await error.getByRole("button", { name: "Try again" }).click();
  await expect(page.getByTestId("reforecast-study")).toBeVisible({ timeout: 30_000 });
});
