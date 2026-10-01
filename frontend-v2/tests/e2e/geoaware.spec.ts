import { expect, test } from "@playwright/test";

// Geography-aware experiment page against the REAL backend: the negative verdict is shown, values equal the hash-verified API,
// and the post-hoc year carries its mandatory label.

const API = "/api/science/evidence/geoaware";

test("the experiment page states the negative verdict and the labelled years from the API", async ({ page }) => {
  const overview = await (await page.request.get(`${API}/overview`)).json();
  const e2025 = await (await page.request.get(`${API}/evaluation?year=2025`)).json();
  expect(overview.decision.adds_value).toBe(false);
  await page.goto("/geoaware");
  await expect(page.getByRole("heading", { level: 1, name: "Geography-Aware Model Experiment" })).toBeVisible();
  await expect(page.getByTestId("geoaware-verdict")).toContainText("Pre-registered rule NOT met");
  await expect(page.locator(".zone-banner-posthoc").filter({ hasText: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST" })).toBeVisible();
  const raw = e2025.payload.pooled.COASTAL_AND_OROGRAPHIC.M2.rmse_mm as number;
  await expect(page.locator("#geo-2025-heading").locator("xpath=ancestor::section").locator("tr", { hasText: "RMSE" }).first()).toContainText(raw.toFixed(2));
  await expect(page.getByText("none: no configuration passed G1, G2 and G3", { exact: false }).first()).toBeVisible();
});

test("the page is reachable from the navigation and usable on a narrow screen", async ({ page }) => {
  await page.goto("/zones");
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Geography-Aware Experiment" }).click();
  await expect(page).toHaveURL(/\/geoaware$/);
  await page.setViewportSize({ width: 390, height: 800 });
  await expect(page.getByTestId("geoaware-verdict")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});
