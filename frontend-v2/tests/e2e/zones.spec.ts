import { expect, test } from "@playwright/test";

// Geographic Forcing Zones page against the REAL backend: values equal the hash-verified API, post-hoc years are labelled,
// unsupported strata are never scored, and the page stays usable on narrow screens.

const API = "/api/science/evidence/zones";
type Block = { status?: string; rmse_mm?: number; bias_mm?: number; categorical?: { heavy?: { status?: string; frequency_bias?: number } } };

async function verification(page: import("@playwright/test").Page, track: string, year: number) {
  const response = await page.request.get(`${API}/verification?track=${track}&year=${year}`);
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<{ evidence_label: string; payload: { case_count: number; models: string[]; pooled: Record<string, Record<string, Block>>; support: Record<string, { heavy: { observed_event_pairs: number } }> } }>;
}

test("the zones page shows the post-hoc label, the map and the pooled values from the API", async ({ page }) => {
  const api = await verification(page, "B", 2025);
  await page.goto("/zones");
  await expect(page.getByRole("heading", { level: 1, name: "Geographic Forcing Zones" })).toBeVisible();
  await expect(page.locator(".zone-banner")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST");
  await expect(page.getByRole("img", { name: /Map of the 49 by 49 land grid/ })).toBeVisible();
  for (const label of ["Coastal", "Orographic", "Coastal and orographic (Ghats coast)", "Other (interior)"]) await expect(page.locator(".zone-legend").getByText(label, { exact: false }).first()).toBeVisible();
  // default score = heavy-rain frequency bias; Raw on the Ghats-coast zone equals the API value
  const raw = api.payload.pooled.COASTAL_AND_OROGRAPHIC.M0.categorical!.heavy!.frequency_bias!;
  const row = page.locator("#zone-skill-heading").locator("xpath=ancestor::section").locator("tr", { hasText: "Coastal and orographic (Ghats coast)" }).first();
  await expect(row).toContainText(raw.toFixed(2));
  await expect(page.getByText("Stage 3, a geography-aware model, is not authorised")).toBeVisible();
});

test("switching population relabels the evidence and changing the score changes the table", async ({ page }) => {
  await page.goto("/zones");
  await page.getByLabel("Population").selectOption("B-2024");
  await expect(page.locator(".zone-banner")).toContainText("development evidence");
  await expect(page.locator(".zone-banner")).not.toContainText("POST-HOC");
  await page.getByLabel("Population").selectOption("A-2019");
  await expect(page.locator(".zone-banner")).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
  const api = await verification(page, "A", 2019);
  expect(api.payload.models).toEqual(["M0", "M2", "M3", "M4"]);
  await expect(page.locator(".zone-table").first().locator("thead th", { hasText: "M1 Ridge" })).toHaveCount(0);
  await page.getByLabel("Score").selectOption({ label: "Bias, forecast minus IMD (mm)" });
  const bias = api.payload.pooled.COASTAL_AND_OROGRAPHIC.M0.bias_mm!;
  await expect(page.locator(".zone-table").first().locator("tr", { hasText: "Coastal and orographic (Ghats coast)" })).toContainText(bias.toFixed(2));
});

test("forcing strata never show a score for a stratum without enough events and the rule panel states its caveat", async ({ page }) => {
  const forcing = await (await page.request.get(`${API}/forcing?track=B&year=2025`)).json() as { payload: { support: Record<string, { heavy_supported: boolean }> } };
  const thin = Object.entries(forcing.payload.support).filter(([, g]) => !g.heavy_supported);
  expect(thin.length).toBeGreaterThan(0);
  await page.goto("/zones");
  await expect(page.getByText("insufficient support").first()).toBeVisible();
  await expect(page.locator("#zone-rule-heading").locator("xpath=ancestor::section")).toContainText("Read with care");
  await expect(page.locator("#zone-forcing-heading").locator("xpath=ancestor::section")).toContainText("training year (2023)");
});

test("the zones page has no horizontal overflow on phone and tablet widths", async ({ page }) => {
  for (const [width, height] of [[375, 812], [768, 1024]]) {
    await page.setViewportSize({ width, height });
    await page.goto("/zones");
    await expect(page.getByRole("heading", { level: 1, name: "Geographic Forcing Zones" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
});

test("the navigation reaches the zones page", async ({ page }) => {
  await page.goto("/live");
  await page.getByRole("link", { name: "Geographic Zones" }).first().click();
  await expect(page).toHaveURL(/\/zones$/);
});
