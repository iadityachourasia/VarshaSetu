import { expect, test } from "@playwright/test";

// Western-disturbance indicator panel against the REAL backend: numbers equal the hash-verified API, the heuristic is labelled, the negative decision is shown, post-hoc years are labelled.

const API = "/api/science/evidence/wd-indicator";
const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the panel labels the indicator a heuristic, shows the no-association decision and numbers equal to the API", async ({ page }) => {
  const results = await Promise.all([2021, 2022, 2024, 2025].map(async (y) => (await page.request.get(`${API}/result?year=${y}`)).json()));
  const overview = await (await page.request.get(`${API}/overview`)).json();
  await page.goto("/regimes");
  await expect(page.getByTestId("wd-indicator")).toBeVisible();
  await expect(page.getByTestId("wd-indicator-banner")).toContainText("Rule-based heuristic, forecast height only, not a validated detection of western disturbances");
  await expect(page.getByTestId("wd-indicator-decision")).toContainText(overview.decision.wording);
  for (const r of results) {
    const row = page.getByTestId(`wd-row-${r.year}`);
    const g = r.payload.groups;
    await expect(row.locator("td").nth(0)).toHaveText(`${g.flagged.cases} / ${g.not_flagged.cases}`);
    await expect(row.locator("td").nth(1)).toHaveText(`${fixed(g.flagged.mean_rain_mm_per_day, 2)} / ${fixed(g.not_flagged.mean_rain_mm_per_day, 2)}`);
    await expect(row.locator("td").nth(2)).toContainText(fixed(r.payload.association.flagged_minus_not_flagged_mean_rain.point, 2));
    await expect(row.locator("td").nth(3)).toContainText(fixed(r.payload.association.spearman.point, 2));
  }
  await expect(page.getByTestId("wd-row-2022")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2022 FINAL TEST");
  await expect(page.getByTestId("wd-row-2025")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST");
});

test("the case lookup shows the frozen flag and index of the selected case and does not claim a detection", async ({ page }) => {
  const served = await (await page.request.get(`${API}/cases?year=2025`)).json();
  const flagged = served.cases.find((c: { flag: boolean | null }) => c.flag === true);
  await page.goto("/regimes");
  const lookup = page.getByTestId("wd-case-lookup");
  await expect(lookup).toBeVisible();
  await lookup.getByRole("combobox").selectOption(flagged.case_id);
  await expect(page.getByTestId("wd-case-reading")).toContainText("Flagged");
  await expect(page.getByTestId("wd-case-reading")).toContainText(`index ${fixed(flagged.index, 2)}`);
  await expect(page.getByTestId("wd-case-reading")).toContainText("does not say a western disturbance is present");
});

test("switching the lookup population changes the case list", async ({ page }) => {
  const a = await (await page.request.get(`${API}/cases?year=2021`)).json();
  await page.goto("/regimes");
  const panel = page.getByTestId("wd-indicator");
  await panel.getByLabel("Population for the case lookup").selectOption("2021");
  await expect(panel.getByTestId("wd-case-lookup").getByRole("combobox").locator("option")).toHaveCount(a.cases.length);
});
