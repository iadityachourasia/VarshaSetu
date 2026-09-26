import { expect, test } from "@playwright/test";

// Phase 5A.2D, spec sections 33-34: Extreme Rain (all four modes) and
// Verification (all seven tabs) against the real live backend. Same caveat
// as operational-track-b.spec.ts: written against this session's own source
// for these two pages, not run here for lack of a live backend with the
// frozen experiments/ corpus (see docs/97 section 2).

test("2025 Extreme Rain Heavy: probability metrics, detection, spatial FSS, and reliability all render live, no PR/ROC curve UI", async ({ page }) => {
  await page.goto("/extremes?experiment=operational&year=2025");
  await expect(page.getByRole("heading", { name: "Extreme Rain" })).toBeVisible();
  await expect(page.getByRole("group", { name: "Rainfall threshold" })).toBeVisible();

  // Probability mode (default): frozen 2025 Heavy scalar metrics.
  await expect(page.getByText("0.01983", { exact: false })).toBeVisible(); // Brier
  await expect(page.getByText("0.895", { exact: false })).toBeVisible(); // ROC-AUC

  // Detection mode: deterministic Raw/M1-M4 CSI, cross-checked against the
  // frozen final_result_2025.json values verified directly in this session.
  await page.getByRole("button", { name: "Detection" }).click();
  await expect(page.getByRole("heading", { name: /Thresholded event detection/ })).toBeVisible();
  const csiRow = page.locator("tr", { hasText: "M1" }).first();
  await expect(csiRow).toContainText("0.0200");

  // Spatial mode: FSS chart, with the explicit non-buried conclusion.
  await page.getByRole("button", { name: "Spatial skill / FSS" }).click();
  await expect(page.getByRole("heading", { name: /Fractions Skill Score/ })).toBeVisible();
  await expect(page.getByText(/Raw GEFS retained stronger extreme-rain spatial FSS/)).toBeVisible();

  // Reliability mode.
  await page.getByRole("button", { name: "Reliability" }).click();
  await expect(page.getByRole("heading", { name: "Reliability bins" })).toBeVisible();

  await expect(page.getByText(/No PR\/ROC curve is rendered anywhere on this page/)).toBeVisible();
});

test("2025 Extreme Rain Very Heavy: high false-alarm-ratio limitation is stated, not buried", async ({ page }) => {
  await page.goto("/extremes?experiment=operational&year=2025");
  await page.getByRole("button", { name: /Very Heavy ≥/ }).click();
  await expect(page.getByText(/the false-alarm ratio is high/)).toBeVisible();
});

test("2023 Extreme Rain: every mode honestly reports unavailability, no fabricated chart", async ({ page }) => {
  await page.goto("/extremes?experiment=operational&year=2023");
  await expect(page.getByText(/unavailable for 2023/)).toBeVisible();
});

test("Verification: 2024 model-selection context and 2025 primary/secondary semantics", async ({ page }) => {
  await page.goto("/verification");
  await expect(page.getByRole("heading", { name: "Model selection story" })).toBeVisible();
  await expect(page.getByText(/M2 achieved a lower secondary 2025 RMSE/)).toBeVisible();

  const tabs = page.getByRole("tablist", { name: "Verification mode" });
  await expect(tabs).toBeVisible();

  await page.getByRole("tab", { name: "Continuous" }).click();
  // Not getByLabel("Year"): ambiguous with the global header's "Experiment
  // and year" select. getByRole("combobox", ...) restricts candidates to
  // this tab's own year <select>.
  const yearSelect = page.getByRole("combobox", { name: /^Year/ });
  await yearSelect.selectOption("2024");
  await expect(page.getByText(/VALIDATION \/ MODEL SELECTION: M1 was selected here/)).toBeVisible();
  await yearSelect.selectOption("2025");
  await expect(page.getByRole("cell", { name: "16.1657" })).toBeVisible(); // frozen 2025 Raw RMSE
  await expect(page.getByRole("cell", { name: "15.5736" })).toBeVisible(); // frozen 2025 M1 RMSE, distinct from the model-selection-story caveat paragraph that also mentions this number
  await expect(page.getByText("Secondary final-test result")).toBeVisible();

  await page.getByRole("tab", { name: "Extremes" }).click();
  await expect(page.getByRole("heading", { name: /Thresholded event detection/ })).toBeVisible();

  await page.getByRole("tab", { name: "Probability" }).click();
  await expect(page.getByText(/Only scalar PR-AUC\/ROC-AUC exist/)).toBeVisible();

  await page.getByRole("tab", { name: "Spatial" }).click();
  // Scoped to this tab's own tabpanel: the page also renders Track A's
  // independent verification charts elsewhere (reusing the same
  // .chart-figure class), which an unscoped locator would also match.
  await expect(page.getByRole("tabpanel").locator(".chart-figure")).toBeVisible();

  await page.getByRole("tab", { name: "Lead Time" }).click();
  await expect(page.getByRole("heading", { name: /2025 lead-time RMSE/ })).toBeVisible();

  await page.getByRole("tab", { name: "Case Outcomes" }).click();
  await expect(page.locator(".phase5-outcome-bar span", { hasText: "improved" })).toBeVisible();
  // "Not every case improved" appears verbatim in both the chart's own
  // figcaption and this surrounding caveat paragraph -- scope to the latter.
  await expect(page.locator("p.phase5-caveat", { hasText: "Not every case improved" })).toBeVisible();

  await page.getByRole("tab", { name: "Generalization" }).click();
  await expect(page.getByRole("heading", { name: "Validation → Final-Test Behavior" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Probability generalization" })).toBeVisible();
  await expect(page.getByText(/Probability discrimination weakened from validation to final test/)).toBeVisible();
});
