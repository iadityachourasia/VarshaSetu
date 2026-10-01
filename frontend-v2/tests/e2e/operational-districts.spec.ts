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
  await expect(page.getByText(/pre-registered primary 2025 final-test model/).first()).toBeVisible();
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

// ---- P0-4: prototype label, compare-all-models view, error map, descriptive history ----------------

test("the district page carries the Historical District Decision-Support Prototype label and no warning claim", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  await expect(page.getByText(/Historical District Decision-Support Prototype/)).toBeVisible();
  await expect(page.getByText(/not an advisory or live warning/)).toBeVisible();
  await expect(page.getByText(/official warning/i)).toHaveCount(0);
});

test("Compare all models shows Raw, M1-M4 and IMD per district, equal to the API, with the improvement definition", async ({ page }) => {
  const api = await (await page.request.get(`/api/science/operational/2025/cases/${CASE_2025}/districts/compare`)).json();
  const top = [...api.districts].sort((a: { observed_mean_mm: number }, b: { observed_mean_mm: number }) => b.observed_mean_mm - a.observed_mean_mm)[0];
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  await page.getByRole("button", { name: "Compare all models" }).click();
  const table = page.getByRole("table", { name: /district comparison of Raw GEFS and all four corrected models/ });
  await expect(table.locator("tbody tr")).toHaveCount(api.districts.length);
  for (const header of ["District", "Raw", "M1", "M2", "M3", "M4", "IMD Mean"]) {
    await expect(table.getByRole("columnheader", { name: new RegExp(`^${header}( [↑↓])?$`) })).toBeVisible();
  }
  const row = table.locator("tbody tr").filter({ hasText: top.district_name }).first();
  const cells = (await row.locator("td").allTextContents()).map((c) => c.trim());
  expect(cells).toEqual([
    `${top.raw_mean_mm.toFixed(1)} mm`, ...["m1", "m2", "m3", "m4"].map((m) => `${top.models[m].mean_mm.toFixed(1)} mm`), `${top.observed_mean_mm.toFixed(1)} mm`,
  ]);
  await page.getByRole("button", { name: /^Error vs IMD/ }).click();
  const errors = (await row.locator("td").allTextContents()).map((c) => c.trim());
  expect(errors[1]).toBe(`${top.models.m1.error_mm > 0 ? "+" : ""}${top.models.m1.error_mm.toFixed(1)} mm`);
  await page.getByRole("button", { name: /^Improvement vs Raw/ }).click();
  await expect(page.getByText(/closer to IMD than Raw/)).toBeVisible();
  await expect(page.getByText(/not a skill score/).first()).toBeVisible();
  const improvement = (await row.locator("td").allTextContents()).map((c) => c.trim());
  expect(improvement[0]).toBe("—");
  expect(improvement[3]).toBe(`${top.models.m3.improvement_vs_raw_mm > 0 ? "+" : ""}${top.models.m3.improvement_vs_raw_mm.toFixed(1)} mm`);
});

test("the error map option shows a labelled diverging legend and the inspector lists every model", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  await expect(page.locator(".district-model-table tbody tr")).toHaveCount(5);
  await page.getByRole("combobox", { name: /^Map shows/ }).selectOption("error");
  await expect(page.getByText(/Selected model error vs IMD \(mm\) · district mean rainfall/)).toBeVisible();
  await expect(page.getByRole("img", { name: /Diverging scale: blue under-forecast/ })).toBeVisible();
  await expect(page.getByText(/a district-mean error for this one case, not a skill score/)).toBeVisible();
  await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
});

test("district history is descriptive: three series over all cases and no skill statistic", async ({ page }) => {
  await page.goto(`/districts?experiment=operational&year=2025&case=${CASE_2025}`);
  const history = page.locator(".district-history");
  await expect(history.getByRole("heading", { name: /district-mean history across \d+ 2025 cases/ })).toBeVisible();
  await expect(history.getByText(/No district-level skill score is computed or implied/)).toBeVisible();
  await expect(history.locator(".recharts-line")).toHaveCount(3);
  const text = (await history.innerText()).toLowerCase();
  for (const token of ["rmse", " csi", " pod", " fss", "skill score:"]) expect(text, token).not.toContain(token);
  const id = await page.evaluate(() => (document.querySelector(".district-table tbody tr.selected-row th button") as HTMLElement | null)?.textContent ?? "");
  expect(id.length).toBeGreaterThan(0);
  await page.getByRole("combobox", { name: /^Corrected model/ }).selectOption("m3");
  await expect(history.getByText(/M3 \(hard regime-routed ML\)/)).toBeVisible();
});

test("2024 supports the compare view and history with the development-year label", async ({ page }) => {
  await page.goto("/districts?experiment=operational&year=2024");
  await expect(page.getByText(/Validation \/ selection year/)).toBeVisible();
  await page.getByRole("button", { name: "Compare all models" }).click();
  await expect(page.locator(".district-compare-table tbody tr").first()).toBeVisible();
  await expect(page.locator(".district-history").getByRole("heading", { name: /across \d+ 2024 cases/ })).toBeVisible();
});
