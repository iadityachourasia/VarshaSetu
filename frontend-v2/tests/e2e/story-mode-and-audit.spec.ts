import { expect, test } from "@playwright/test";
import { COMPLIANCE_PAGE } from "./helpers/features";

// The presentation has one scene fewer while the requirement-coverage page (and its summary scene) is hidden.
const SCENES = COMPLIANCE_PAGE ? 15 : 14;

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
  await expect(page.getByText(`Scene 1 of ${SCENES}`)).toBeVisible();
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
  await expect(page.getByText(`Scene 1 of ${SCENES}`)).toBeVisible();

  // Walk to the last scene and confirm the closing content + Exit control.
  for (let i = 0; i < SCENES - 1; i++) await page.keyboard.press("ArrowRight");
  await expect(page.getByText(`Scene ${SCENES} of ${SCENES}`)).toBeVisible();
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

test("Story Mode figures equal the verified API values (nothing is typed into the scenes)", async ({ page }) => {
  const comparison = await (await page.request.get("/api/science/model-comparison")).json();
  const rawRmse = comparison.results.M0_RAW_GEFS.overall.continuous.rmse_mm as number;
  const m2Rmse = comparison.results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm as number;
  const deterministic = await (await page.request.get("/api/science/operational/2025/metrics/deterministic")).json();
  const m0 = deterministic.metrics.M0.continuous.rmse_mm as number;
  const m1 = deterministic.metrics.M1.continuous.rmse_mm as number;
  const probability = await (await page.request.get("/api/science/operational/2025/metrics/probability")).json();
  const heavyBss = (probability.metrics.heavy.metrics?.bss ?? probability.metrics.heavy.bss) as number;
  const quality = await (await page.request.get("/api/science/operational/quality")).json();
  const change = (raw: number, corrected: number) => { const c = ((corrected - raw) / raw) * 100; return `${c >= 0 ? "+" : "−"}${Math.abs(c).toFixed(2)}%`; };

  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  const goTo = async (title: string) => { for (let i = 0; i < 15 && !(await dialog.getByRole("heading", { name: title }).isVisible()); i++) await page.keyboard.press("ArrowRight"); await expect(dialog.getByRole("heading", { name: title })).toBeVisible(); };

  await goTo("Extreme Probability");
  await expect(dialog).toContainText(`${heavyBss >= 0 ? "+" : "−"}${Math.abs(heavyBss).toFixed(4)}`);
  await goTo("2019 Benchmark");
  await expect(dialog).toContainText(`${rawRmse.toFixed(2)} mm`);
  await expect(dialog).toContainText(`${m2Rmse.toFixed(2)} mm`);
  await expect(dialog).toContainText(change(rawRmse, m2Rmse));
  await goTo("2025 Final Test");
  await expect(dialog).toContainText(`${m0.toFixed(2)} mm`);
  await expect(dialog).toContainText(`${m1.toFixed(2)} mm`);
  await expect(dialog).toContainText(change(m0, m1));
  await goTo("Data Quality");
  await expect(dialog).toContainText(Number(quality.scheduled_date_lead_cases).toLocaleString("en-GB"));
  await expect(dialog).toContainText(Number(quality.c00_eligible_total).toLocaleString("en-GB"));
});

test("Story Mode shows no number for the 2019 scene when the verified API is unreachable", async ({ page }) => {
  await page.route("**/api/science/model-comparison", (route) => route.abort());
  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  for (let i = 0; i < 15 && !(await dialog.getByRole("heading", { name: "2019 Benchmark" }).isVisible()); i++) await page.keyboard.press("ArrowRight");
  await expect(dialog.getByRole("heading", { name: "2019 Benchmark" })).toBeVisible();
  await expect(dialog.getByText(/not reachable right now, so no number is shown/)).toBeVisible();
  await expect(dialog.locator(".story-stat-row")).toHaveCount(0);
  // the 2025 scene is generated from the frozen bundle, so it still renders its figures
  for (let i = 0; i < 15 && !(await dialog.getByRole("heading", { name: "2025 Final Test" }).isVisible()); i++) await page.keyboard.press("ArrowRight");
  await expect(dialog.locator(".story-stat-row")).toHaveCount(1);
});

test("Story Mode: the coverage, regime and reforecast scenes show the values of their own verified endpoints", async ({ page }) => {
  // The coverage endpoint is closed unless the page is shown (the backend answers 404), so it is read only in that configuration.
  const coverage = COMPLIANCE_PAGE ? await (await page.request.get("/api/science/evidence/ps-coverage")).json() : null;
  const r03 = await (await page.request.get("/api/science/evidence/reforecast/r03")).json();
  const confirmation = await (await page.request.get("/api/science/evidence/reforecast/r05-confirmation")).json();
  const total = coverage ? Object.values(coverage.counts as Record<string, number>).reduce((a, b) => a + b, 0) : 0;
  const mandatory = coverage ? Object.values(coverage.mandatory_counts as Record<string, number>).reduce((a, b) => a + b, 0) : 0;

  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  const goTo = async (title: string) => { for (let i = 0; i < 15 && !(await dialog.getByRole("heading", { name: title }).isVisible()); i++) await page.keyboard.press("ArrowRight"); await expect(dialog.getByRole("heading", { name: title })).toBeVisible(); };

  await goTo("Regimes Against Observation");
  await expect(dialog).toContainText((r03.payload.tasks.ACTIVE.auc.point as number).toFixed(3));
  await expect(dialog).toContainText((r03.payload.tasks.WESTERN_DISTURBANCE.auc.point as number).toFixed(3));
  await goTo("Sealed Reforecast Years");
  await expect(dialog).toContainText(`${(confirmation.payload.pooled.M0.rmse_mm as number).toFixed(2)} → ${(confirmation.payload.pooled.B1_shifted.rmse_mm as number).toFixed(2)}`);
  await expect(dialog).toContainText(confirmation.payload.bundle_decision.decision.tier);
  if (coverage) {
    await goTo("Requirement Coverage");
    await expect(dialog).toContainText(`${coverage.counts.IMPLEMENTED} of ${total}`);
    await expect(dialog).toContainText(`${coverage.mandatory_counts.IMPLEMENTED} of ${mandatory}`);
  }
});

test("Story Mode: the scene list jumps to a scene and marks the current one", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  await dialog.getByRole("navigation", { name: "Scenes" }).getByRole("button", { name: /Sealed Reforecast Years/ }).click();
  await expect(dialog.getByRole("heading", { name: "Sealed Reforecast Years" })).toBeVisible();
  await expect(dialog.getByRole("navigation", { name: "Scenes" }).getByRole("button", { name: /Sealed Reforecast Years/ })).toHaveAttribute("aria-current", "step");
  await expect(dialog.getByText(`Scene 11 of ${SCENES}`)).toBeVisible();
});

test("while hidden, the requirement-coverage page is not linked, not served and not in the presentation", async ({ page }) => {
  test.skip(COMPLIANCE_PAGE, "the page is shown in this build");
  await page.goto("/live");
  await expect(page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "SIH26080 Compliance" })).toHaveCount(0);
  expect((await page.goto("/compliance"))?.status()).toBe(404);
  await page.goto("/");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  const dialog = page.getByRole("dialog", { name: "Present VarshaSetu" });
  await expect(dialog.getByRole("navigation", { name: "Scenes" }).getByRole("button", { name: /Requirement Coverage/ })).toHaveCount(0);
  await expect(dialog.getByText(`Scene 1 of ${SCENES}`)).toBeVisible();
});

test("while hidden, the coverage endpoint answers exactly like an unknown path", async ({ page }) => {
  test.skip(COMPLIANCE_PAGE, "the coverage endpoint is open in this configuration");
  const closed = await page.request.get("/api/science/evidence/ps-coverage");
  const unknown = await page.request.get("/api/science/evidence/no-such-endpoint");
  expect(closed.status()).toBe(404);
  expect(await closed.json()).toEqual(await unknown.json());
});
