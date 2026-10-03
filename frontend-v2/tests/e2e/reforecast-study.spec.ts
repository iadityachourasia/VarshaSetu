import { expect, test } from "@playwright/test";

// Reforecast study against the REAL backend: numbers equal the hash-verified API, the sealed-test label is shown, the honest findings are stated.

const API = "/api/science/evidence/reforecast";
const fixed = (value: number | null | undefined, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the Verification Lab shows the sealed-year heavy-rain comparison with numbers equal to the API and the bias finding", async ({ page }) => {
  const r05 = await (await page.request.get(`${API}/r05`)).json();
  await page.goto("/verification");
  const panel = page.getByTestId("reforecast-study");
  await expect(panel).toBeVisible();
  await expect(page.getByTestId("reforecast-banner")).toContainText("POST-UNSEAL SEALED TEST 2014-2016: first use of these years");
  for (const m of ["M0", "B0", "B1", "R_hard", "R_soft"]) {
    const row = page.getByTestId(`reforecast-row-${m}`);
    const x = r05.payload.pooled[m];
    await expect(row.locator("td").nth(0)).toHaveText(fixed(x.rmse_mm, 3));
    await expect(row.locator("td").nth(2)).toContainText(`${fixed(x.heavy.csi, 3)} /`);
  }
  const exc = r05.payload.exceedance["B1:very_heavy"];
  await expect(page.getByTestId("reforecast-exc-B1").locator("td").nth(1)).toContainText(`${fixed(exc.test.csi, 3)} /`);
  await expect(page.getByTestId("reforecast-bundle-B0")).toContainText(`tier ${r05.payload.bundle_decisions.B0.decision.tier}`);
  await expect(page.getByTestId("reforecast-bundle-B0")).toContainText("bias within limits: no");
  await expect(page.getByTestId("reforecast-regime-R_soft")).toContainText("is not shown to add value");
});

test("the confirmatory round shows the added parameter, the corrected bias and the frozen verdict equal to the API", async ({ page }) => {
  const c = await (await page.request.get(`${API}/r05-confirmation`)).json();
  await page.goto("/verification");
  await expect(page.getByTestId("reforecast-confirmation-banner")).toContainText("CONFIRMATORY TEST 2017-2019");
  await expect(page.getByTestId("reforecast-confirmation-banner")).toContainText(`${fixed(c.payload.delta_mm, 2)} mm`);
  await expect(page.getByTestId("reforecast-confirmation-bundle").locator("td").nth(0)).toHaveText(fixed(c.payload.pooled.B1_shifted.rmse_mm, 3));
  await expect(page.getByTestId("reforecast-confirmation-bundle").locator("td").nth(1)).toHaveText(fixed(c.payload.pooled.B1_shifted.bias_mm, 3));
  await expect(page.getByTestId("reforecast-confirmation-uncorrected").locator("td").nth(1)).toHaveText(fixed(c.payload.pooled.B1_uncorrected.bias_mm, 3));
  await expect(page.getByTestId("reforecast-confirmation-decision")).toContainText(`tier ${c.payload.bundle_decision.decision.tier}`);
  await expect(page.getByTestId("reforecast-confirmation-decision")).toContainText("bias within limits: yes");
});

test("Regime Intelligence shows the five detection tasks with verdicts equal to the API", async ({ page }) => {
  const r03 = await (await page.request.get(`${API}/r03`)).json();
  await page.goto("/regimes");
  await expect(page.getByTestId("regime-task-validation")).toBeVisible();
  await expect(page.getByTestId("regime-task-banner")).toContainText("POST-UNSEAL SEALED TEST 2014-2016");
  for (const [task, t] of Object.entries(r03.payload.tasks) as [string, { cases: number; positives: number; negatives: number; auc: { point: number } }][]) {
    const row = page.getByTestId(`regime-task-row-${task}`);
    await expect(row.locator("td").nth(0)).toContainText(`${t.cases} (${t.positives} / ${t.negatives})`);
    await expect(row.locator("td").nth(1)).toContainText(fixed(t.auc.point, 3));
    await expect(row.locator("td").nth(4)).toContainText("validated and useful");
  }
});

test("both reforecast sections fit a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  for (const route of ["/verification", "/regimes"]) {
    await page.goto(route);
    await expect(page.getByTestId(route === "/verification" ? "reforecast-study" : "regime-task-validation")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  }
});
