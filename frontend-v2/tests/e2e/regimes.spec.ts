import { expect, test, type Page } from "@playwright/test";

// Regime Intelligence for both tracks against the REAL backend and tracked evidence (docs/108).
// There must be no "Feature in Development" state, every consumed holdout must carry its post-hoc label,
// and the displayed numbers must equal the evidence API.

async function evidence(page: Page, track: "A" | "B", year: number) {
  const response = await page.request.get(`/api/science/evidence/regime-verification?track=${track}&year=${year}`);
  expect(response.ok()).toBeTruthy();
  return response.json();
}

const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("Track A regime page is a real workbench with evidence, not a development placeholder", async ({ page }) => {
  await page.goto("/regimes");
  await expect(page.getByRole("heading", { level: 1, name: "Regime Intelligence" })).toBeVisible();
  await expect(page.getByText("Feature in Development")).toHaveCount(0);
  await expect(page.getByText("Forecast-only pseudo-regime classifier output · not observed meteorological truth")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Selected case · classifier probabilities" })).toBeVisible();
  await expect(page.getByLabel("Forecast-only regime probabilities")).toBeVisible();
  await expect(page.getByText(/Coastal, orographic and western-disturbance regimes are not yet part of the classifier/)).toBeVisible();
  const panel = page.locator(".regime-evidence");
  await expect(panel).toBeVisible();
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST")).toBeVisible();
  await expect(panel.getByText(/REPRODUCED \(175 checks/)).toBeVisible();
});

test("Track A table values equal the evidence API (by regime, by lead, FSS with defined-case counts)", async ({ page }) => {
  const data = await evidence(page, "A", 2019);
  await page.goto("/regimes?year=2019");
  const panel = page.locator(".regime-evidence");
  await expect(panel).toBeVisible();
  const regimeTable = panel.getByRole("table", { name: "CSI by forecast-only pseudo-regime" });
  await expect(regimeTable.locator("tbody tr")).toHaveCount(4);
  const all = regimeTable.locator("tbody tr").last();
  const cells = await all.locator("td").allTextContents();
  const expected = ["M0", "M1", "M2", "M3", "M4"].map((m) => fixed(data.overall.categorical.heavy[m].CSI, 3));
  expect(cells.map((c) => c.split(" ")[0])).toEqual(expected);
  await expect(panel.getByRole("table", { name: "CSI by lead day" }).locator("tbody tr")).toHaveCount(3);
  await panel.getByRole("button", { name: "FSS", exact: true }).click();
  await panel.getByRole("button", { name: "5×5" }).click();
  const fssAll = await panel.getByRole("table", { name: "FSS by forecast-only pseudo-regime" }).locator("tbody tr").last().locator("td").allTextContents();
  expect(fssAll.map((c) => c.split(" ")[0])).toEqual(["M0", "M1", "M2", "M3", "M4"].map((m) => fixed(data.overall.fss.heavy["5"].all_cases[m].fss, 3)));
  expect(fssAll[0]).toContain(`n=${data.overall.fss.heavy["5"].all_cases.M0.case_count}`);
});

test("Track A 2018 is labelled development evidence and 2017 has an honest training-year note", async ({ page }) => {
  await page.goto("/regimes?year=2018");
  await expect(page.locator(".regime-evidence").getByText(/2018 validation year: development evidence/)).toBeVisible();
  await expect(page.getByText(/published for the 2019 final-test cases only/)).toBeVisible();
  await page.goto("/regimes?year=2017");
  await expect(page.getByText(/2017 is the classifier training year/)).toBeVisible();
  await expect(page.getByText(/No regime-stratified verification is published for Track A 2017/)).toBeVisible();
  await expect(page.locator(".regime-evidence table")).toHaveCount(0);
});

test("Track B keeps its classifier view and adds labelled regime-aware verification for 2024 and 2025", async ({ page }) => {
  await page.goto("/regimes?experiment=operational&year=2025");
  await expect(page.getByRole("heading", { name: "2025 deterministic model consequence" })).toBeVisible();
  const panel = page.locator(".regime-evidence");
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST")).toBeVisible();
  await panel.getByRole("button", { name: "Very Heavy ≥ 115.6 mm / 24 h" }).click();
  await panel.getByRole("button", { name: "Forecast / observed events" }).click();
  await expect(panel.getByRole("table", { name: /Forecast \/ observed events by forecast-only pseudo-regime/ })).toBeVisible();
  await expect(panel.getByText(/near 0 mean the model forecasts almost no events/)).toBeVisible();
  await page.goto("/regimes?experiment=operational&year=2024");
  await expect(page.locator(".regime-evidence").getByText(/2024 validation\/selection year: development evidence/)).toBeVisible();
  await page.goto("/regimes?experiment=operational&year=2023");
  await expect(page.getByText(/training \/ cross-fit year/)).toBeVisible();
  await expect(page.locator(".regime-evidence table")).toHaveCount(0);
});

test("paired differences state whether the interval excludes zero and never hide undefined values", async ({ page }) => {
  await page.goto("/regimes?experiment=operational&year=2025");
  const table = page.locator(".regime-evidence").getByRole("table", { name: /Paired bootstrap differences/ });
  await expect(table.locator("tbody tr")).toHaveCount(6);
  await expect(table).toContainText(/interval (excludes|includes) 0/);
  await page.getByRole("button", { name: "Very Heavy ≥ 115.6 mm / 24 h" }).click();
  await page.locator(".regime-evidence").getByRole("button", { name: "CSI", exact: true }).click();
  await expect(page.locator(".regime-evidence").getByRole("table", { name: "CSI by lead day" })).toContainText("0.000");
});

test("regime page has no horizontal overflow on phone and tablet widths", async ({ page }) => {
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/regimes");
    await expect(page.locator(".regime-evidence")).toBeVisible();
    const dimensions = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(dimensions.page, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(dimensions.viewport + 1);
  }
});
