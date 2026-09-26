import { expect, test } from "@playwright/test";

// Phase 5A.2D, spec section 36. Unlike the other two new operational specs,
// this one intercepts the live operational API at the browser network layer
// with page.route() rather than hitting a real backend -- there is no way to
// safely "simulate" a SCIENCE_INTEGRITY_FAILURE against a real backend
// without corrupting a real frozen artifact (forbidden by AGENTS.md), so
// mocking is the only safe way to exercise this path. Because the mock
// intercepts before any request reaches the (possibly absent) backend, this
// file runs correctly with no backend at all -- verified in this session
// against a real headless-Chromium `next start` (see docs/97 section 2).

test("genuine network failure falls back to the verified static bundle, with the fallback indicator shown", async ({ page }) => {
  await page.route("**/api/science/operational/2025/cases*", (route) => route.abort("failed"));
  await page.goto("/casebook?experiment=operational&year=2025");
  await expect(page.getByRole("heading", { name: "Event Casebook" })).toBeVisible();
  // The static bundle covers the case list, so real case rows still render.
  await expect(page.locator(".phase5-case-row").first()).toBeVisible();
  await expect(page.getByText("Cached frozen presentation data")).toBeVisible();
});

test("SCIENCE_INTEGRITY_FAILURE never falls back -- hard stop, not masked by cached data", async ({ page }) => {
  await page.route("**/api/science/operational/2025/cases*", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "simulated integrity failure for e2e test" }),
  }));
  await page.goto("/casebook?experiment=operational&year=2025");
  await expect(page.getByText(/Scientific artifact integrity check failed/)).toBeVisible();
  await expect(page.getByText(/This is a hard failure and is not masked by cached data/)).toBeVisible();
  await expect(page.locator(".phase5-case-row")).toHaveCount(0);
  await expect(page.getByText("Cached frozen presentation data")).toHaveCount(0);
});
