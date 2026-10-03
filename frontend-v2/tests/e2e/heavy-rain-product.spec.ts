import { expect, test } from "@playwright/test";

// The frozen heavy-rain bundle (B1) in the 2019 map and district products, against the REAL backend (docs/143).

const CASE = "20190802T000000Z_day3_24h";
const API = "/api/science/heavy-rain";
const LABEL = "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST";

test("Forecast Explorer: choosing B1 swaps the corrected panel, says what it is, and M2 comes back unchanged", async ({ page }) => {
  const b1 = await (await page.request.get(`${API}/cases/${CASE}`)).json();
  await page.goto(`/forecast?case=${CASE}`);
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect(page.getByText("Frozen M2 Global XGBoost")).toBeVisible();
  await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /B1/ }).click();
  await expect(page.getByTestId("heavy-rain-notice")).toContainText(LABEL);
  await expect(page.getByTestId("heavy-rain-notice")).toContainText("RMSE B1");
  await expect(page.getByText("B1 event-weighted regression + mean-error shift (reforecast study)")).toBeVisible();
  await expect(page.getByText(/Corrected RMSE \(B1\)/)).toContainText(`${(b1.b1_rmse_mm as number).toFixed(1)} mm`);
  await expect(page.getByText("FSS is not computed for the B1 layer.")).toBeVisible();
  await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /M2/ }).click();
  await expect(page.getByText("Frozen M2 Global XGBoost")).toBeVisible();
  await expect(page.getByText(/Corrected RMSE \(M2\)/)).toBeVisible();
});

test("Forecast Explorer: if the B1 layer cannot be verified, the panel stays M2 and says so", async ({ page }) => {
  await page.route(`**${API}/cases/**`, (route) => route.abort());
  await page.goto(`/forecast?case=${CASE}`);
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /B1/ }).click();
  await expect(page.getByText(/could not be verified, so the corrected panel still shows the frozen global model M2/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Frozen M2 Global XGBoost")).toBeVisible();
});

test("Extreme Rain: the classifier output carries its own quality figures, equal to the frozen overview", async ({ page }) => {
  const overview = await (await page.request.get(`${API}/overview`)).json();
  const heavy = overview.summary.classifier.heavy;
  const very = overview.summary.classifier.very_heavy;
  await page.goto(`/extremes?case=${CASE}`);
  await expect(page.getByRole("heading", { name: "Probability quality" })).toBeVisible();
  await page.getByRole("group", { name: "Heavy-rain output" }).getByRole("button", { name: /classifier B1/ }).click();
  const view = page.getByTestId("classifier-view");
  await expect(view).toBeVisible();
  await expect(page.getByTestId("heavy-rain-notice")).toContainText(LABEL);
  await expect(page.getByRole("heading", { name: "Classifier quality" })).toBeVisible();
  await expect(view).toContainText((heavy.csi as number).toFixed(3));
  await expect(view).toContainText(`POD ${(heavy.pod as number).toFixed(3)}`);
  await expect(view).toContainText(`False alarms ${(heavy.false_alarms as number).toLocaleString("en-US")}`);
  await page.getByRole("group", { name: "Event threshold" }).getByRole("button", { name: /Very Heavy/ }).click();
  await expect(view).toContainText(`POD ${(very.pod as number).toFixed(3)}`);
  await expect(page.getByTestId("classifier-confirmation")).toContainText(overview.confirmation.cases.toString());
  await expect(page.getByText("not a calibrated probability").first()).toBeVisible();
  await page.getByRole("group", { name: "Classifier layer" }).getByRole("button", { name: /yes \/ no/ }).click();
  await expect(page.getByText("Forecast: yes (score at or above it)")).toBeVisible();
  // the calibrated reliability material belongs to the other output and is not shown for the classifier
  await expect(page.getByRole("heading", { name: "Reliability" })).toHaveCount(0);
  await page.getByRole("group", { name: "Heavy-rain output" }).getByRole("button", { name: /Calibrated probability/ }).click();
  await expect(page.getByRole("heading", { name: "Reliability" })).toBeVisible();
});

test("District Intelligence: B1 rows equal the served district aggregation and the columns say score and flagged area", async ({ page }) => {
  const body = await (await page.request.get(`${API}/cases/${CASE}/districts`)).json();
  const top = [...body.districts].sort((a: { corrected_mean_mm: number }, b: { corrected_mean_mm: number }) => b.corrected_mean_mm - a.corrected_mean_mm)[0];
  await page.goto(`/districts?case=${CASE}`);
  await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
  await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /B1/ }).click();
  await expect(page.getByTestId("heavy-rain-notice")).toContainText(LABEL);
  const header = page.locator("table.district-table thead");
  await expect(header).toContainText("Heavy score");
  await expect(header).toContainText("Heavy flagged area");
  const row = page.locator("table.district-table tbody tr").first();
  await expect(row).toContainText(top.district_name);
  await expect(row).toContainText(`${(top.corrected_mean_mm as number).toFixed(1)} mm`);
  await expect(row).toContainText((top.heavy_probability as number).toFixed(2));
  await expect(row).toContainText(`${((top.heavy_flag_area_fraction as number) * 100).toFixed(1)}%`);
  await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /M2/ }).click();
  await expect(header).toContainText("Heavy P");
});

test("the layer is served read-only and refuses an unknown case", async ({ page }) => {
  expect((await page.request.get(`${API}/cases/20190101T000000Z_day1_24h`)).status()).toBe(404);
  expect((await page.request.post(`${API}/overview`)).status()).toBe(405);
});
