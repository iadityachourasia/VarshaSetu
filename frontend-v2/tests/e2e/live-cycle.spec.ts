import { expect, test } from "@playwright/test";

// Experimental live-cycle page against the REAL backend. The bundles are local worker output (not tracked), so the checks adapt to what exists:
// the labelled banner and the API's own status message are always required; cycle content is checked against the API when a bundle exists.

const API = "/api/science/live";
const fixed = (value: number, digits: number) => value.toFixed(digits);

test("the page states what exists, labels it experimental and never presents a replay as a live cycle", async ({ page }) => {
  const status = await (await page.request.get(`${API}/status`)).json();
  await page.goto("/live");
  await expect(page.getByRole("heading", { level: 1, name: "Experimental Live Cycle" })).toBeVisible();
  await expect(page.getByTestId("live-status-message")).toHaveText(status.message);
  if (status.cycles.length === 0) {
    await expect(page.getByText("No cycle bundle exists")).toBeVisible();
    await expect(page.getByTestId("live-banner")).toContainText("EXPERIMENTAL FORECAST: frozen models, no verification yet, not an official warning");
    return;
  }
  const current = status.latest_live ?? status.cycles[0];
  await expect(page.getByTestId("live-banner")).toContainText(current.label);
  if (!status.has_live_cycle) {
    await expect(page.getByTestId("live-banner")).toContainText("not a forecast");
    await expect(page.getByTestId("live-status-message")).toContainText("Only historical replays");
  }
  await expect(page.getByTestId("live-provenance")).toContainText("no observation read, no retraining or recalibration");
  if (current.season_scope === "OUTSIDE_JJAS_RESEARCH_SCOPE") {
    await expect(page.getByTestId("live-season-scope")).toContainText("no October skill or reliability claim");
  }
});

test("statistics and regime probabilities equal the API and the map is drawn for the selected lead", async ({ page }) => {
  const status = await (await page.request.get(`${API}/status`)).json();
  test.skip(status.cycles.length === 0, "no local bundle published");
  const current = status.latest_live ?? status.cycles[0];
  const detail = await (await page.request.get(`${API}/cycle?kind=${current.kind}&date=${current.cycle}`)).json();
  const product = current.products[0];
  await page.goto("/live");
  await expect(page.getByTestId("live-map")).toBeVisible();
  await expect(page.getByLabel("Field")).toHaveValue("M2");
  await expect(page.getByTestId("live-model-default")).toContainText("M2 global XGBoost");
  const stats = detail.domain_statistics[product].M1;
  const row = page.getByTestId("live-stats").locator("tr", { hasText: detail.fields.M1 });
  await expect(row).toContainText(fixed(stats.mean, 3));
  await expect(row).toContainText(fixed(stats.max, 3));
  const regime = detail.regime_probabilities[product];
  await expect(page.getByTestId("live-regime")).toContainText(fixed(regime.ACTIVE_MONSOON, 3));
  await expect(page.getByTestId("live-applicability")).toContainText(detail.applicability.status);
  await page.getByLabel("Field").selectOption("heavy_probability");
  await expect(page.getByTestId("live-probability-status")).toContainText("reliability unverified");
  if (current.kind === "replay") await expect(page.getByTestId("live-replay-gate")).toContainText("frozen 2025 artifacts");
  for (const [withheld, why] of Object.entries(current.withheld_products as Record<string, string>)) {
    await expect(page.getByTestId("live-withheld")).toContainText(why);
    await expect(page.getByLabel("Lead").locator("option")).not.toContainText([withheld]);
  }
});

test("the page is reachable from the navigation and usable on a narrow screen", async ({ page }) => {
  await page.goto("/zones");
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Experimental Live Cycle" }).click();
  await expect(page).toHaveURL(/\/live$/);
  await page.setViewportSize({ width: 390, height: 800 });
  await expect(page.getByTestId("live-banner")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("regional district rows match the verified forecast-only API", async ({ page }) => {
  const status = await (await page.request.get(`${API}/status`)).json();
  test.skip(status.cycles.length === 0, "no local bundle published");
  const current = status.latest_live ?? status.cycles[0];
  const product = current.products[0];
  const response = await page.request.get(`${API}/districts?kind=${current.kind}&date=${current.cycle}&product=${product}&model=M2`);
  expect(response.ok()).toBeTruthy();
  const data = await response.json();
  await page.goto("/live");
  await page.getByTestId("live-district-toggle").click();
  await expect(page.getByTestId("live-district-provenance")).toContainText(`${data.district_count} regional districts`);
  await expect(page.getByTestId("live-district-provenance")).toContainText(data.evidence_manifest_sha256.slice(0, 8));
  await expect(page.getByTestId("live-district-probability-status")).toContainText("not district-wide exceedance chances");
  const first = data.districts[0];
  const row = page.getByTestId("live-district-table").locator("tr", { hasText: first.district_name });
  await expect(row).toContainText(fixed(first.corrected_mean_mm, 1));
  await expect(row).toContainText(fixed(first.heavy_probability, 3));
  await page.getByLabel("Find district").fill(first.district_name);
  await expect(row).toBeVisible();
});
