import { expect, test } from "@playwright/test";

// Phase 5B: the ?demo=official presentation preset and Presentation View.
// Both are fully client-navigable without a live backend (the redirect
// itself needs no data, and Forecast's operational path has a real static
// fallback for the case list), so both were run and pass against a real
// headless Chromium in this session (see docs/99 section 2).

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

test("Presentation View: button toggle collapses sidebar and hides non-context header controls", async ({ page }) => {
  await page.goto("/observations");
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeVisible();

  await page.getByRole("button", { name: "Presentation View", exact: true }).click();
  await expect(page.getByRole("button", { name: "Exit Presentation View" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeHidden();
  // Sidebar nav links remain present (interactive), just labels are hidden.
  await expect(page.getByRole("link", { name: "Six-Season Observations" })).toBeAttached();

  await page.getByRole("button", { name: "Exit Presentation View" }).click();
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeVisible();
});

test("Presentation View: P keyboard shortcut toggles it, and is ignored while typing in a form control", async ({ page }) => {
  await page.goto("/observations");
  // Wait for hydration (the keydown listener attaches in a useEffect, which
  // only runs post-hydration) so the keypress below isn't racing the page
  // becoming interactive.
  await page.waitForLoadState("networkidle");
  await page.keyboard.press("p");
  await expect(page.getByRole("button", { name: "Exit Presentation View" })).toBeVisible();
  await page.keyboard.press("p");
  await expect(page.getByRole("button", { name: "Presentation View", exact: true })).toBeVisible();

  const monthSelect = page.getByLabel("Observation month");
  await monthSelect.focus();
  await page.keyboard.press("p");
  await expect(page.getByRole("button", { name: "Presentation View", exact: true })).toBeVisible(); // unchanged, not toggled
});
