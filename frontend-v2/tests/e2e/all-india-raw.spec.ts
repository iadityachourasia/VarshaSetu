import { expect, test } from "@playwright/test";

// All-India Raw verification section against the REAL backend: numbers equal the hash-verified API, the Raw-only scope is stated, the consumed years carry their labels.

const API = "/api/science/evidence/all-india-raw";
const fixed = (value: number | null | undefined, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the section states it is Raw only and its numbers equal the API for the selected year", async ({ page }) => {
  const result = await (await page.request.get(`${API}/result?year=2025`)).json();
  await page.goto("/verification");
  const panel = page.getByTestId("all-india-raw");
  await expect(panel).toBeVisible();
  await expect(page.getByTestId("all-india-raw-banner")).toContainText("Raw only, outside the regional domain no correction exists");
  await expect(page.getByTestId("all-india-raw-year-label")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST");
  for (const region of ["ALL_INDIA", "INSIDE_MODEL_DOMAIN", "EAST_AND_NORTH_EAST", "SOUTH_OF_DOMAIN"]) {
    const row = page.getByTestId(`all-india-row-${region}`);
    const m = result.payload.metrics[region];
    await expect(row.locator("td").nth(0)).toHaveText(String(result.payload.region_cells_with_observation[region]));
    await expect(row.locator("td").nth(1)).toContainText(fixed(m.rmse_mm, 2));
    await expect(row.locator("td").nth(2)).toContainText(fixed(m.bias_mm, 2));
    const heavy = m.categorical.heavy;
    await expect(row.locator("td").nth(3)).toContainText("status" in heavy ? "insufficient support" : `CSI ${fixed(heavy.CSI, 3)}`);
  }
});

test("switching the year changes the label and the table and never hides the Raw-only scope", async ({ page }) => {
  const r2023 = await (await page.request.get(`${API}/result?year=2023`)).json();
  await page.goto("/verification");
  const panel = page.getByTestId("all-india-raw");
  await panel.getByLabel("All-India year").selectOption("2023");
  await expect(page.getByTestId("all-india-raw-year-label")).toContainText("training year of the downstream models");
  await expect(page.getByTestId("all-india-row-ALL_INDIA").locator("td").nth(1)).toContainText(fixed(r2023.payload.metrics.ALL_INDIA.rmse_mm, 2));
  await expect(page.getByTestId("all-india-raw-banner")).toContainText("Raw only");
});
