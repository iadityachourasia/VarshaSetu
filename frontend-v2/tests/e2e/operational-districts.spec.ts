import { expect, test, type Page } from "@playwright/test";

// Track B district product (2024 validation year, 2025 consumed holdout) against the REAL backend
// and frozen artifacts. 2023 has no district product and must say so instead of fabricating a table.

const CASE_2025 = "20250714_day2_24h";

async function pick(page: Page, label: RegExp, value: string) {
  await page.getByRole("combobox", { name: label }).selectOption(value);
}

test("2025 district product shows raw, corrected and IMD replay per district with honest labels", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  await expect(page.getByRole("heading", { name: "District Intelligence" })).toBeVisible();
  await expect(page.getByText(/historical replay, not an advisory or live warning/)).toBeVisible();
  const table = page.getByRole("table", { name: /Area-weighted district rainfall, event probabilities and IMD replay/ });
  await expect(table).toBeVisible();
  await expect(table.locator("tbody tr")).toHaveCount(187);
  for (const header of ["Raw Mean", "Corrected Mean", "IMD Mean", "Corrected − IMD", "Heavy P", "Very Heavy P", "Corrected Heavy Area", "IMD Heavy Area"]) {
    await expect(table.getByRole("columnheader", { name: new RegExp(`^${header}( [↑↓])?$`) })).toBeVisible();
  }
  await expect(page.getByText(/Consumed final-test holdout \(historical replay\)/)).toBeVisible();
  await expect(page.getByText(/pre-registered primary 2025 final-test model/)).toBeVisible();
  await expect(page.getByText(/Forecast-only pseudo-regime/)).toBeVisible();
  await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
  await expect(page.locator(".district-detail")).toContainText("IMD observed mean");
});

test("district table sorts by a column and the inspector follows a selected district", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  const table = page.getByRole("table", { name: /Area-weighted district rainfall/ });
  await expect(table.locator("tbody tr")).toHaveCount(187);
  await table.getByRole("button", { name: /^District/ }).click();
  const names = await table.locator("tbody th").allTextContents();
  expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b)));
  await table.locator("tbody th button").nth(3).click();
  await expect(page.locator(".district-detail h2")).toHaveText(names[3]);
});

test("switching the corrected model and map variable re-renders without inventing a value", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  await expect(page.locator(".district-table tbody tr")).toHaveCount(187);
  await pick(page, /^Corrected model/, "m3");
  await expect(page.getByText(/hard regime-routed ML/)).toBeVisible();
  await expect(page.locator(".district-table tbody tr")).toHaveCount(187);
  await pick(page, /^Map shows/, "observed");
  await expect(page.getByText(/IMD observed mean \(replay\) · district mean rainfall/)).toBeVisible();
});

test("2024 is labelled validation/selection and 2023 has an honest no-district-product state", async ({ page }) => {
  await page.goto("/districts?experiment=operational&year=2024");
  await expect(page.getByText(/Validation \/ selection year/)).toBeVisible();
  await expect(page.locator(".district-table tbody tr").first()).toBeVisible();
  await page.goto("/districts?experiment=operational&year=2023");
  await expect(page.getByText("No district product for 2023", { exact: true })).toBeVisible();
  await expect(page.locator(".district-table")).toHaveCount(0);
});
