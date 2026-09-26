import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Phase 5A.2D, spec sections 37-38: accessibility and responsive checks on
// the two rebuilt pages, using mocked live-API routes (page.route()) rather
// than a real backend so this suite runs deterministically regardless of
// whether the frozen experiments/ corpus is present. Verified passing in
// this session against a real headless Chromium (2 axe scans, 0 critical/
// serious violations; 3 responsive breakpoints, 0px overflow). Casebook and
// Extreme Rain fetch entirely client-side and are fully covered here;
// Verification is not, because its page.tsx does its Track-A getScience(...)
// calls server-side during SSR (server=true), which page.route() cannot
// intercept -- confirmed directly in this session (see docs/97 section 2).

function makeCase(i: number) {
  const lead = [24, 48, 72][i % 3];
  return {
    case_id: `20250${600 + i}_day${(i % 3) + 1}_24h`, year: 2025,
    initialization_utc: `2025-07-${String((i % 28) + 1).padStart(2, "0")}T00:00:00Z`,
    lead_hours: lead, product: "gefs", year_role: "FINAL_TEST", source_complete: true,
    deterministic_source_eligible: true, probability_source_eligible: true, regime_source_eligible: true,
    ensemble_source_eligible: i % 3 === 0, c00_rainfall_qc_pass: true, full_5_member_rainfall_qc_pass: i % 3 === 0,
    m1_rmse_mm: 15 + (i % 5), raw_rmse_mm: 16 + (i % 5), m1_minus_raw_rmse_mm: (i % 2 === 0 ? -1 : 1) * (i % 3),
    initialization_date: "2025-07-01", month: 7, lead_label: `Day ${(i % 3) + 1}`, valid_date: "2025-07-02",
    event_heavy: i % 5 === 0, event_very_heavy: i % 20 === 0,
    pseudo_regime_class: ["ACTIVE_MONSOON", "BREAK_WEAK_MONSOON", "LOW_DEPRESSION_INFLUENCED"][i % 3],
    selected_model_improved_vs_raw: i % 2 === 0,
  };
}
const cases = Array.from({ length: 40 }, (_, i) => makeCase(i));

const availability = {
  year: 2025, role: "FINAL_TEST", role_label: "2025 completed final test",
  raw_rainfall: true, imd_observation: true, m1: "case_grid", m2: "case_grid", m3: "case_grid", m4: "case_grid",
  heavy_probability: "case_grid", very_heavy_probability: "case_grid", regime_probability: "per_case",
  atmosphere_fields: true, ensemble_members: "eligible_subset_only", case_level_metrics: true, per_cell_metrics: true,
  fss: true, reliability_bins: true, pr_roc_curve_arrays: "unavailable", district_aggregates: false, notes: [],
};

const probabilityMetric = {
  brier: 0.0198313, bss: 0.09483, pr_auc: 0.21736, roc_auc: 0.89455, observed_event_count: 6760,
  categorical: { decision_threshold_probability: 0.1, metrics: { POD: 0.27796, FAR: 0.69576, CSI: 0.16994, ETS: 0.15942 } },
  reliability: [{ bin_lower: 0, bin_upper: 0.1, mean_predicted_probability: 0.01, observed_event_frequency: 0.02, sample_count: 1000 }],
};
const deterministicModel = {
  case_count: 232, cell_count: 301832, continuous: { rmse_mm: 15.5736, mae_mm: 7.58, bias_mm: -1.2 },
  heavy: { metrics: { POD: 0.2, FAR: 0.6, CSI: 0.02, ETS: 0.018 } },
  very_heavy: { metrics: { POD: 0.1, FAR: 0.8, CSI: 0.01, ETS: 0.009 } },
  leads: { 24: { continuous: { rmse_mm: 15.35 } }, 48: { continuous: { rmse_mm: 15.28 } }, 72: { continuous: { rmse_mm: 16.04 } } },
};
const fssScale = { matched_raw: { fss: 0.0912 }, matched_selected: { fss: 0.0392 }, matched_case_count: 214 };
const fssEvent = { "1": fssScale, "3": fssScale, "5": fssScale, "9": fssScale };

test.beforeEach(async ({ page }) => {
  await page.route("**/api/science/operational/*/cases*", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ year: 2025, total: cases.length, page: 1, page_size: 400, cases }),
  }));
  await page.route("**/api/science/operational/*/availability", (route) => route.fulfill({
    status: 200, contentType: "application/json", body: JSON.stringify(availability),
  }));
  await page.route("**/api/science/operational/*/cases/*/probability/*", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ case_id: cases[0].case_id, year: 2025, target: "heavy", threshold_probability: 0.1, calibration_type: "isotonic", values: Array.from({ length: 49 }, () => Array.from({ length: 49 }, () => Math.random() * 0.3)), prediction_role: "FINAL_TEST_PREDICTION" }),
  }));
  await page.route("**/api/science/operational/*/metrics/probability", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ year: 2025, metrics: { heavy: probabilityMetric, very_heavy: probabilityMetric }, curve_arrays: "unavailable" }),
  }));
  await page.route("**/api/science/operational/*/metrics/fss", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ year: 2025, fss: { heavy: fssEvent, very_heavy: fssEvent }, neighborhoods: [1, 3, 5, 9] }),
  }));
  await page.route("**/api/science/operational/*/metrics/deterministic", (route) => route.fulfill({
    status: 200, contentType: "application/json",
    body: JSON.stringify({ year: 2025, metrics: { M0: deterministicModel, M1: deterministicModel, M2: deterministicModel, M3: deterministicModel, M4: deterministicModel }, primary_model: "M1", notes: [] }),
  }));
});

// /verification is deliberately excluded here: its page.tsx does its Track-A
// getScience(...) calls server-side (server=true, a direct Node fetch during
// SSR), which page.route() cannot intercept -- only OperationalVerification's
// own client-side queries are interceptable. Confirmed by trying it: without
// a real Track-A backend the whole page bails to the top-level ErrorState
// before OperationalVerification ever mounts. Not a defect in this session's
// code; a real environment limitation. See docs/97 section 2/19.
for (const route of ["/casebook", "/extremes"] as const) {
  test(`axe: ${route} (mocked live data) has no critical/serious violations`, async ({ page }) => {
    await page.goto(`${route}?experiment=operational&year=2025`);
    await expect(page.locator("main h1, main h2").first()).toBeVisible();
    const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    const bad = scan.violations.filter((v) => ["critical", "serious"].includes(v.impact ?? ""));
    console.log(route, JSON.stringify(bad.map((v) => ({ id: v.id, impact: v.impact, nodes: v.nodes.length, help: v.help })), null, 2));
    expect(bad).toEqual([]);
  });
}

test("responsive: Extreme Rain has no horizontal overflow at 1366x768 / 1440x900 / 1920x1080", async ({ page }) => {
  for (const [width, height] of [[1366, 768], [1440, 900], [1920, 1080]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto("/extremes?experiment=operational&year=2025");
    await expect(page.getByRole("heading", { name: "Extreme Rain" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `horizontal overflow at ${width}x${height}`).toBeLessThanOrEqual(1);
  }
});
