import { expect, test, type Page } from "@playwright/test";

// Phase 5A.2D, spec sections 32-35. These specs exercise the live Track-B
// (2023-2025 historical operational GEFS) flows against the REAL backend and
// REAL frozen artifacts, the same way the pre-existing demo-flow/mapping
// specs already do for Track A -- no mocking here, since docs/93-96 record
// that this data genuinely exists in the project's real environment (the
// experiments/ corpus this container itself lacks; see docs/97 section 2 for
// exactly what could and could not be executed in THIS sandboxed session).
// Selectors below were written against the actual source of each page
// (operational-workspace.tsx, operational-casebook.tsx, operational-
// ensemble.tsx, regime-intelligence.tsx, operational-extremes.tsx,
// operational-verification.tsx) rather than guessed, but were not run here
// for lack of a live backend -- see docs/97 for the honest status.

async function selectOperationalYear(page: Page, year: 2023 | 2024 | 2025) {
  await page.getByLabel("Experiment and year").selectOption(`operational:${year}`);
  await page.waitForURL(new RegExp(`experiment=operational&year=${year}`));
}

test("2023 Forecast shows only the out-of-fold M2 model, never claimed as an independent test", async ({ page }) => {
  await page.goto("/forecast");
  await selectOperationalYear(page, 2023);
  await expect(page.getByRole("heading", { name: "Forecast & Atmosphere" })).toBeVisible();
  // Not getByLabel("Model"): the wrapping <label> makes the select's own
  // accessible name include its option text, and that same substring also
  // appears in nearby map region/img aria-labels ("... frozen model map" /
  // "... frozen model 49 by 49 ..."), so getByLabel("Model") is ambiguous
  // (strict-mode violation). getByRole("combobox", ...) is unambiguous
  // because it restricts candidates to the actual <select>.
  const modelSelect = page.getByRole("combobox", { name: /^Model/ });
  await expect(modelSelect.locator("option")).toHaveCount(1);
  await expect(modelSelect.locator("option")).toHaveText("M2 cross-fit / OOF");
  await expect(page.getByRole("region", { name: "M2 cross-fit / OOF map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Raw operational GEFS map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "IMD observed map" })).toBeVisible();
  await expect(page.getByText(/M2 is an out-of-fold prediction, not an independent test result/)).toBeVisible();
});

test("2024 Forecast offers M1-M4 against IMD, labeled as validation evidence", async ({ page }) => {
  await page.goto("/forecast");
  await selectOperationalYear(page, 2024);
  const modelSelect = page.getByRole("combobox", { name: /^Model/ });
  for (const model of ["M1", "M2", "M3", "M4"]) {
    await modelSelect.selectOption(model);
    await expect(modelSelect).toHaveValue(model);
    await expect(page.getByRole("region", { name: new RegExp(`^${model} `) })).toBeVisible();
  }
  await expect(page.getByRole("region", { name: "IMD observed map" })).toBeVisible();
  await expect(page.getByText(/2024 validation \/ model-selection evidence; not the final test/)).toBeVisible();
});

test("2025 Forecast defaults to Raw versus preselected M1 against IMD", async ({ page }) => {
  await page.goto("/forecast");
  await selectOperationalYear(page, 2025);
  await expect(page.getByLabel("Model")).toHaveValue("M1");
  await expect(page.getByRole("region", { name: "Raw operational GEFS map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "M1 Ridge MOS map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "IMD observed map" })).toBeVisible();
  await expect(page.getByText(/POST-HOC EXPLORATORY VIEW OF THE COMPLETED FINAL TEST/)).toBeVisible();
});

test("Casebook: select an observed event, open it in Forecast", async ({ page }) => {
  await page.goto("/casebook");
  await selectOperationalYear(page, 2025);
  await expect(page.getByRole("heading", { name: "Event Casebook" })).toBeVisible();
  await page.getByLabel("Observed event").selectOption("heavy");
  const firstCase = page.locator(".phase5-case-row").first();
  await expect(firstCase).toBeVisible();
  const href = await firstCase.getAttribute("href");
  expect(href).toMatch(/^\/forecast\?experiment=operational&year=2025&case=/);
  await firstCase.click();
  await expect(page.getByRole("heading", { name: "Forecast & Atmosphere" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(href!.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
});

test("Ensemble: all five member statuses are listed, QC-failed members not silently dropped", async ({ page }) => {
  await page.goto("/ensemble?experiment=operational&year=2025");
  await expect(page.getByRole("heading", { name: "Ensemble & Uncertainty" })).toBeVisible();
  await expect(page.getByText("MATCHED 75-CASE SUBSET")).toBeVisible();
  for (const member of ["c00", "p01", "p02", "p03", "p04"]) {
    await expect(page.getByText(member, { exact: false }).first()).toBeVisible();
  }
  await expect(page.getByRole("heading", { name: "Matched-population probability comparison" })).toBeVisible();
  await expect(page.getByText(/QC-failed members remain listed, never silently dropped/)).toBeVisible();
});

test("Regime: correct year-role wording across 2023 OOF / 2024 prospective / 2025 final", async ({ page }) => {
  await page.goto("/regimes?experiment=operational&year=2023");
  await expect(page.getByRole("heading", { name: "Regime Intelligence" })).toBeVisible();
  await expect(page.getByText(/out-of-fold cross-fit pathway/)).toBeVisible();

  // Not getByLabel("Year"): it's ambiguous with the global header's
  // "Experiment and year" select, whose accessible name contains "year" as
  // a case-insensitive substring. getByRole("combobox", ...) restricted to
  // this page's own Year control avoids the collision.
  const yearSelect = page.getByRole("combobox", { name: /^Year/ });
  await yearSelect.selectOption("2024");
  await expect(page.getByText(/frozen prospective-validation prediction/)).toBeVisible();

  await yearSelect.selectOption("2025");
  await expect(page.getByText("Active Monsoon", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "2025 deterministic model consequence" })).toBeVisible();
});

test("Track A regression: 2019 Forecast/Extremes/Verification/Districts unaffected by the Track-B migration", async ({ page }) => {
  await page.goto("/forecast");
  await expect(page.getByRole("region", { name: "Raw GEFS map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "VarshaSetu Corrected map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "IMD Observed map" })).toBeVisible();

  await page.goto("/extremes");
  await expect(page.getByRole("heading", { name: "Extreme Rain" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Heavy rainfall probability map" })).toBeVisible();

  await page.goto("/verification");
  await expect(page.getByText("9.73% lower RMSE")).toBeVisible();
  await expect(page.getByRole("heading", { name: "2025 operational-era historical benchmark" })).toBeVisible();
  await expect(page.getByText(/different GEFS lineages with different evaluation populations/i)).toBeVisible();

  await page.goto("/districts");
  await expect(page.getByRole("heading", { name: "District Intelligence" })).toBeVisible();
});
