import { expect, test } from "@playwright/test";

// Phase 5A.3, sections 39-53 (Story Mode) and 34-38 (Provenance DAG,
// Holdout Governance, Limitations panel); scene order/titles updated in
// Phase 5B section 12-13 to match the official 12-scene sequence exactly.
// All four pages/features here are fully client-side with no live-backend
// dependency, so unlike most of this phase's other new surfaces these were
// actually run and pass against a real headless Chromium in this session
// (see docs/99 section 2).

test("Story Mode: launch, next, back, keyboard, exit", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  await expect(dialog).toBeVisible();
  const geometry = await dialog.evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return { left: rect.left, top: rect.top, width: rect.width, height: rect.height, viewportWidth: innerWidth, viewportHeight: innerHeight };
  });
  expect(geometry).toMatchObject({ left: 0, top: 0, width: geometry.viewportWidth, height: geometry.viewportHeight });
  await expect(dialog.locator(".story-identity")).toContainText("VarshaSetu");
  await expect(page.locator(".app-shell")).toHaveAttribute("inert", "");
  await expect(page.getByText("Scene 1 of 12")).toBeVisible();
  await expect(page.getByRole("heading", { name: "The Problem" })).toBeVisible();

  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByRole("heading", { name: "Two Experiment Tracks" })).toBeVisible();

  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("heading", { name: "Forecast Case" })).toBeVisible();

  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("heading", { name: "Two Experiment Tracks" })).toBeVisible();

  await page.getByRole("button", { name: "← Back" }).click();
  await expect(page.getByRole("heading", { name: "The Problem" })).toBeVisible();
  await expect(page.getByRole("button", { name: "← Back" })).toBeDisabled();

  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Present VarshaSetu" })).not.toBeVisible();
  await expect(page.locator(".app-shell")).not.toHaveAttribute("inert", "");
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeFocused();

  // Re-enter: must start fresh at scene 1, not resume where it left off.
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  await expect(page.getByText("Scene 1 of 12")).toBeVisible();

  // Walk to the last scene and confirm the closing content + Exit control.
  for (let i = 0; i < 11; i++) await page.keyboard.press("ArrowRight");
  await expect(page.getByText("Scene 12 of 12")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Reproducibility" })).toBeVisible();
  await expect(page.getByText("Research prototype for scientifically transparent")).toBeVisible();
  await page.getByRole("button", { name: "Exit", exact: true }).last().click();
  await expect(page.getByRole("dialog", { name: "Present VarshaSetu" })).not.toBeVisible();
});

test("Story Mode: product remains fully usable without it", async ({ page }) => {
  // /observations is fully client-side (no Track-A server-side fetch), so it
  // renders in this backend-less container unlike "/" -- see docs/98 section
  // 2 for why "/" itself could not be used for this check here.
  await page.goto("/observations");
  await expect(page.getByRole("heading", { name: "Six-Season Observations" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("Six-Season Observations: month x year heatmap renders", async ({ page }) => {
  await page.goto("/observations");
  await expect(page.getByRole("heading", { name: "Six-Season Observations" })).toBeVisible();
  await expect(page.getByText("Not a climatology or climate-trend analysis.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Six-season month × year matrix" })).toBeVisible();
  await expect(page.locator(".phase5-heatmap-table")).toBeVisible();
  await page.getByLabel("Metric").selectOption("heavy_cells");
  await expect(page.locator(".phase5-heatmap-table")).toBeVisible();
});

test("Audit: provenance DAG and limitations panel render, node click updates detail", async ({ page }) => {
  await page.goto("/audit");
  await expect(page.getByRole("heading", { name: "Scientific Audit" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Holdout governance lifecycle" })).toBeVisible();
  await expect(page.getByText("CONSUMED", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Experiment lineage (Track B)" })).toBeVisible();
  await page.getByRole("button", { name: "Regime Classifier" }).click();
  await expect(page.getByRole("heading", { name: "Regime Classifier", exact: true })).toBeVisible();
  await expect(page.getByText(/Depends on: M2, Rainfall/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Known limitations" })).toBeVisible();
  await expect(page.getByText(/PR\/ROC curve point arrays are not available/)).toBeVisible();
});
