import { expect, test } from "@playwright/test";

// Geography-aware experiment page against the REAL backend: the negative verdict is shown, values equal the hash-verified API,
// and the post-hoc year carries its mandatory label.

const API = "/api/science/evidence/geoaware";

test("the experiment page states the negative verdict and the labelled years from the API", async ({ page }) => {
  const overview = await (await page.request.get(`${API}/overview`)).json();
  const e2025 = await (await page.request.get(`${API}/evaluation?year=2025`)).json();
  expect(overview.decision.adds_value).toBe(false);
  await page.goto("/geoaware");
  await expect(page.getByRole("heading", { level: 1, name: "Geography-Aware Model Experiment" })).toBeVisible();
  await expect(page.getByTestId("geoaware-verdict")).toContainText("Pre-registered rule NOT met");
  await expect(page.locator(".zone-banner-posthoc").filter({ hasText: "POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST" })).toBeVisible();
  const raw = e2025.payload.pooled.COASTAL_AND_OROGRAPHIC.M2.rmse_mm as number;
  await expect(page.locator("#geo-2025-heading").locator("xpath=ancestor::section").locator("tr", { hasText: "RMSE" }).first()).toContainText(raw.toFixed(2));
  await expect(page.getByText("none: no configuration passed G1, G2 and G3", { exact: false }).first()).toBeVisible();
});

test("the page is reachable from the navigation and usable on a narrow screen", async ({ page }) => {
  await page.goto("/zones");
  await page.getByRole("navigation", { name: "Primary" }).getByRole("link", { name: "Geography-Aware Experiment" }).click();
  await expect(page).toHaveURL(/\/geoaware$/);
  await page.setViewportSize({ width: 390, height: 800 });
  await expect(page.getByTestId("geoaware-verdict")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(1);
});

test("the follow-up section shows the independent 2022 test, its disclosures and numbers equal to the API", async ({ page }) => {
  const api = await (await page.request.get(`${API}/followup`)).json();
  expect(api.sealed_test.opened).toBe(true);
  expect(api.test_2022.label).toBe("INDEPENDENT TEST: first use of this year");
  await page.goto("/geoaware");
  const section = page.getByTestId("geoaware-followup");
  await expect(section).toBeVisible();
  await expect(page.getByTestId("geoaware-sealed")).toContainText("2022 was opened once");
  await expect(page.getByTestId("geoaware-sealed")).toContainText("INDEPENDENT TEST: first use of this year");
  await expect(page.getByTestId("geoaware-claim")).toContainText(api.test_2022.claim_wording);
  await expect(page.getByTestId("geoaware-claim")).toContainText("97.5 percent, not 95 percent");
  await expect(section).toContainText("not an unbiased selection");
  for (const [key, d] of Object.entries<{ adds_value: boolean | null; zone_heavy_csi_difference: { point: number } }>(api.test_2022.decisions)) {
    const row = page.getByTestId(`decision-${key}`);
    await expect(row).toContainText(`${d.zone_heavy_csi_difference.point >= 0 ? "+" : ""}${d.zone_heavy_csi_difference.point.toFixed(3)}`);
    await expect(row.locator("td").last()).toHaveText(d.adds_value == null ? "unevaluable" : d.adds_value ? "yes" : "no");
  }
  const primary = api.test_2022.candidate_sets.v3_primary;
  const frequencyBias = api.test_2022.pooled_summary[primary.candidate].zone_heavy_frequency_bias.toFixed(2);
  await expect(page.getByTestId("geoaware-test-reading")).toContainText(`frequency bias is ${frequencyBias}`);
  await expect(page.getByTestId("geoaware-test-reading")).toContainText("mild over-forecasting");
  const b1 = api.v3_selection.B1;
  await expect(section.getByRole("row", { name: /^B1 geography/ })).toContainText(`#${b1.grid_index}`);
  await expect(section.getByRole("row", { name: /^M0 Raw forecast/ })).toBeVisible();
});

test("the follow-up section never claims 2022 is sealed and states the secondary candidate did not pass", async ({ page }) => {
  await page.goto("/geoaware");
  const section = page.getByTestId("geoaware-followup");
  await expect(section).toBeVisible();
  await expect(section).not.toContainText("is sealed and has not been opened");
  await expect(page.getByTestId("decision-v2_secondary").locator("td").last()).toHaveText("no");
  await expect(section).toContainText("secondary (v2) candidate set did not pass");
});
