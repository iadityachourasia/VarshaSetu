import { expect, test } from "@playwright/test";

// The official demo preset remains available in the shared header.

test("demo=official redirects to the canonical operational forecast URL and renders", async ({ page }) => {
  await page.goto("/forecast?demo=official");
  await expect(page).toHaveURL(/\/forecast\?experiment=operational&year=2025&case=20250714_day2_24h/);
  await expect(page.getByRole("heading", { name: "Forecast & Atmosphere" })).toBeVisible();
});

test("Reset Demo link restores the official experiment/year/case", async ({ page }) => {
  await page.goto("/observations");
  await page.getByRole("link", { name: "Reset Demo" }).click();
  await expect(page).toHaveURL(/\/forecast\?experiment=operational&year=2025&case=20250714_day2_24h/);
});

test("shared header keeps Present VarshaSetu without Presentation View", async ({ page }) => {
  await page.goto("/observations");
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Presentation View" })).toHaveCount(0);
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  await expect(page.getByRole("dialog", { name: "Present VarshaSetu" })).toBeVisible();
});
