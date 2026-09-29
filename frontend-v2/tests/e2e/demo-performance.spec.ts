import { expect, test } from "@playwright/test";

test("representative production demo timings", async ({ page }) => {
  const timings: Record<string, number> = {};
  let start = performance.now();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "VarshaSetu" })).toBeVisible();
  timings.overview_ms = Math.round(performance.now() - start);
  start = performance.now();
  await page.getByRole("link", { name: /Explore 2019 forecast intelligence/i }).click();
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  timings.forecast_navigation_and_science_layers_ms = Math.round(performance.now() - start);
  start = performance.now();
  await page.getByLabel("Demo cases").selectOption("20190807T000000Z_day2_24h");
  await expect(page).toHaveURL(/20190807T000000Z_day2_24h/);
  await expect(page.locator(".case-skill-values")).toContainText("49.5 mm");
  timings.case_switch_ms = Math.round(performance.now() - start);
  start = performance.now();
  await page.getByRole("link", { name: "Verification" }).click();
  await expect(page.getByRole("heading", { name: "Fractions Skill Score" })).toBeVisible();
  timings.verification_navigation_ms = Math.round(performance.now() - start);
  console.log("PRODUCTION_DEMO_TIMINGS " + JSON.stringify(timings));
});
