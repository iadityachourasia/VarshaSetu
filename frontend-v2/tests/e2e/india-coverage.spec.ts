import { expect, test } from "@playwright/test";

test("the India-wide page renders a real hashed Raw grid and keeps correction regional", async ({ page }) => {
  const catalogueResponse = await page.request.get("/api/science/evidence/all-india-raw/cases?year=2025");
  expect(catalogueResponse.ok()).toBeTruthy();
  const catalogue = await catalogueResponse.json();
  const available = catalogue.cases.filter((entry: { available_locally: boolean }) => entry.available_locally);
  test.skip(available.length === 0, "ignored local all-India Raw cache is unavailable");
  await page.goto("/india");
  await expect(page.getByRole("heading", { level: 1, name: "India-wide Rainfall Coverage" })).toBeVisible();
  await expect(page.getByTestId("india-coverage-boundary")).toContainText("M2 correction has been scientifically supported only");
  await expect(page.getByTestId("india-raw-map").getByRole("img", { name: /129 by 135 historical rainfall grid/ })).toBeVisible();
  const selected = await page.getByTestId("india-case-select").inputValue();
  const gridResponse = await page.request.get(`/api/science/evidence/all-india-raw/grid?year=2025&case_id=${selected}`);
  expect(gridResponse.ok()).toBeTruthy();
  const grid = await gridResponse.json();
  await expect(page.getByTestId("india-grid-provenance")).toContainText(grid.raw_array_sha256.slice(0, 8));
  await expect(page.getByTestId("india-case-meta")).toContainText(`+${grid.accumulation_window_hours[0]} to +${grid.accumulation_window_hours[1]} h`);
  await page.getByTestId("india-footprint-select").selectOption("full");
  await expect(page.getByTestId("india-footprint-select")).toHaveValue("full");
  await expect(page.getByTestId("india-region-verification")).toContainText("Raw GEFS verification by region");
  await expect(page.getByRole("link", { name: /Open this case in the regional/ })).toHaveAttribute("href", new RegExp(selected));
});

test("the India-wide route is in primary navigation and readable on a narrow screen", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Explore India-wide Raw rainfall/ }).click();
  await expect(page).toHaveURL(/\/india$/);
  await page.goto("/forecast");
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "India-wide Raw Forecast" }).click();
  await expect(page).toHaveURL(/\/india$/);
  await page.setViewportSize({ width: 390, height: 800 });
  await expect(page.getByTestId("india-coverage-boundary")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});

test("the opt-in nationwide development map displays sealed research and no-promotion status", async ({ page }) => {
  const overviewResponse = await page.request.get("/api/science/research/nationwide/overview");
  test.skip(overviewResponse.status() === 404, "local nationwide research API is disabled or its ignored artifacts are unavailable");
  expect(overviewResponse.ok()).toBeTruthy();
  const overview = await overviewResponse.json();
  expect(overview.nationwide_promotion_eligible).toBe(false);
  await page.goto("/india");
  await page.getByTestId("nationwide-research-toggle").click();
  await expect(page.getByTestId("nationwide-research-boundary")).toContainText("no promotion");
  await expect(page.getByTestId("nationwide-research-boundary")).toContainText("failed its prespecified 2023 selection gate");
  const verificationResponse = await page.request.get("/api/science/research/nationwide/verification?region=ALL_INDIA&lead_hours=24");
  expect(verificationResponse.ok()).toBeTruthy();
  const verification = await verificationResponse.json();
  expect(verification.independent_skill_claim).toBe(false);
  expect(new Set(Object.values(verification.models).map((arm) => (arm as { cells: number }).cells))).toEqual(new Set([verification.paired_cells]));
  await expect(page.getByTestId("nationwide-verification-table")).toContainText("FSS 5");
  await expect(page.getByTestId("nationwide-verification-support")).toContainText(verification.score_sha256.slice(0, 8));
  await expect(page.getByTestId("nationwide-research-map").getByRole("img", { name: /129 by 135 historical rainfall grid/ })).toBeVisible();
  await page.getByTestId("nationwide-field-select").selectOption("very_heavy_p");
  await expect(page.getByTestId("nationwide-research-map")).toContainText("Very-heavy probability");
  await expect(page.getByText(/independent probability reliability is unverified/i)).toBeVisible();
  await expect(page.getByText(/non-official/i).first()).toBeVisible();
  const research = page.getByTestId("nationwide-research");
  const districtTable = research.getByRole("table", { name: "Non-official research district mean forecast" });
  await expect(districtTable.locator("tbody tr")).toHaveCount(20);
  const firstDistrict = await districtTable.locator("tbody tr").first().innerText();
  await research.getByRole("button", { name: "Next", exact: true }).click();
  await expect(districtTable.locator("tbody tr").first()).not.toHaveText(firstDistrict);
});
