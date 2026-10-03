import { expect, test } from "@playwright/test";

// Coastal/orographic forcing regime panel against the REAL backend: numbers equal the hash-verified API, the heuristic is labelled, post-hoc years are labelled, the case lookup follows the evidence.

const API = "/api/science/evidence/coastal-regime";
const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the panel labels the regime a heuristic, shows the decision and numbers equal to the API", async ({ page }) => {
  const results = await Promise.all([2018, 2019, 2024, 2025].map(async (y) => (await page.request.get(`${API}/result?year=${y}`)).json()));
  const overview = await (await page.request.get(`${API}/overview`)).json();
  await page.goto("/regimes");
  const panel = page.getByTestId("coastal-regime");
  await expect(panel).toBeVisible();
  await expect(page.getByTestId("coastal-regime-banner")).toContainText("Rule-based heuristic, forecast fields only, not a validated regime and not a probability");
  await expect(page.getByTestId("coastal-regime-decision")).toContainText(overview.decision.wording);
  for (const r of results) {
    const row = page.getByTestId(`coastal-row-${r.year}`);
    const g = r.payload.groups;
    await expect(row.locator("td").nth(0)).toHaveText(`${g.WEAK.cases} / ${g.MODERATE.cases} / ${g.STRONG.cases}`);
    const d = r.payload.discrimination.strong_minus_weak_heavy_fraction;
    await expect(row.locator("td").nth(3)).toContainText(fixed(d.point, 3));
    await expect(row.locator("td").nth(4)).toContainText(fixed(r.payload.discrimination.spearman.point, 2));
  }
  await expect(page.getByTestId("coastal-row-2019")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
  await expect(page.getByTestId("coastal-row-2025")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST");
});

test("the case lookup shows the frozen class and index of the selected case and calls the percentile a rank", async ({ page }) => {
  const served = await (await page.request.get(`${API}/cases?year=2025`)).json();
  const strong = served.cases.find((c: { class: string }) => c.class === "STRONG");
  await page.goto("/regimes");
  const lookup = page.getByTestId("coastal-case-lookup");
  await expect(lookup).toBeVisible();
  await lookup.getByRole("combobox").selectOption(strong.case_id);
  await expect(page.getByTestId("coastal-case-reading")).toContainText("Strong Ghats-coast forcing");
  await expect(page.getByTestId("coastal-case-reading")).toContainText(`index ${fixed(strong.index, 1)}`);
  await expect(page.getByTestId("coastal-case-reading")).toContainText("a rank, not a probability of rain");
});

test("switching the lookup population changes the case list", async ({ page }) => {
  const a = await (await page.request.get(`${API}/cases?year=2019`)).json();
  await page.goto("/regimes");
  const panel = page.getByTestId("coastal-regime");
  await panel.getByLabel("Population for the case lookup").selectOption("2019");
  const options = panel.getByTestId("coastal-case-lookup").getByRole("combobox").locator("option");
  await expect(options).toHaveCount(a.cases.length);
});
