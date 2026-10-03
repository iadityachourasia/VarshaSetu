import { expect, test } from "@playwright/test";

// Independent regime validation panel against the REAL backend: numbers equal the hash-verified API, unsupported tasks never show a score, post-hoc years are labelled.

const API = "/api/science/evidence/regime-validation";
const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the panel states the partial scope, shows scored tasks equal to the API and never scores an unsupported task", async ({ page }) => {
  const [a2019, b2024, b2025] = await Promise.all([2019, 2024, 2025].map(async (y) => (await page.request.get(`${API}/result?year=${y}`)).json()));
  await page.goto("/regimes?experiment=operational&year=2025");
  const panel = page.getByTestId("regime-validation");
  await expect(panel).toBeVisible();
  await expect(page.getByTestId("regime-validation-banner")).toContainText("Partial validation, not the published classification, depression not validated");
  for (const [year, api] of [[2019, a2019], [2024, b2024]] as const) {
    const t = api.payload.tasks.active_vs_not_active;
    expect(t.status).toBe("scored");
    const row = page.getByTestId(`validation-row-${year}`);
    await expect(row.locator("td").nth(2)).toContainText(fixed(t.balanced_accuracy, 3));
    await expect(row.locator("td").nth(2)).toContainText(`[${fixed(t.balanced_accuracy_bootstrap.interval95[0], 3)}, ${fixed(t.balanced_accuracy_bootstrap.interval95[1], 3)}]`);
  }
  expect(b2025.payload.tasks.active_vs_not_active.status).toBe("insufficient_support");
  await expect(page.getByTestId("validation-row-2025").locator("td").nth(2)).toContainText("insufficient support");
  await expect(page.getByTestId("validation-row-2025").locator("td").nth(2).locator("strong")).toHaveCount(0);
  for (const year of [2018, 2019, 2024, 2025]) await expect(page.getByTestId(`validation-row-${year}`).locator("td").nth(3)).toContainText("insufficient support");     // break is validated in no population
  await expect(page.getByTestId(`validation-row-2019`)).toContainText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
  await expect(page.getByTestId("regime-validation-reading")).toContainText("below the chance level of 0.5");
  await expect(page.getByTestId("regime-validation-reading")).toContainText("does not correspond to observed active spells");
});

test("the confusion table follows the selected population and equals the API", async ({ page }) => {
  const api = await (await page.request.get(`${API}/result?year=2024`)).json();
  await page.goto("/regimes");
  const panel = page.getByTestId("regime-validation");
  await panel.getByRole("combobox").selectOption("2024");
  const table = page.getByTestId("validation-confusion");
  const low = api.payload.confusion_predicted_class_by_observed_state.LOW_DEPRESSION_INFLUENCED;
  const row = table.locator("tbody tr").nth(2);
  await expect(row.locator("td").nth(0)).toHaveText(String(low.ACTIVE));
  await expect(row.locator("td").nth(2)).toHaveText(String(low.NEUTRAL));
});

test("the panel is present on the reforecast view too and does not overflow a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto("/regimes");
  await expect(page.getByTestId("regime-validation")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});
