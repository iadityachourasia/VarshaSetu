import { readFileSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

// District-level verification (protocol v1, docs/112) against the REAL backend and hash-verified evidence.

async function openTab(page: Page) {
  await page.goto("/verification");
  await page.getByRole("tab", { name: "District-level" }).click();
  const panel = page.getByRole("tabpanel").locator(".district-verification");      // the operational-era tab; Track A has its own panel on the same page
  await expect(panel).toBeVisible();
  return panel;
}

const fixed = (value: number | null, digits: number) => (value == null ? "undefined" : value.toFixed(digits));

test("the District-level tab shows the frozen protocol, the post-hoc label and equals the evidence API", async ({ page }) => {
  const api = await (await page.request.get("/api/science/evidence/district-verification?year=2025")).json();
  const panel = await openTab(page);
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST")).toBeVisible();
  await expect(panel.getByText(/approved and frozen \(SHA-256 9b348063a6ac/)).toBeVisible();
  await expect(panel.getByText(/REPRODUCED \(14 checks\)/)).toBeVisible();
  await expect(panel.getByText(/169 of 188 districts included/)).toBeVisible();
  const pooled = panel.getByRole("table", { name: /Pooled district-mean RMSE, MAE and bias/ });
  const cells = await pooled.locator("tbody tr").nth(2).locator("td").allTextContents();
  const m2 = api.continuous.pooled.all.M2;
  expect(cells.slice(0, 3)).toEqual([fixed(m2.rmse_mm, 2), fixed(m2.mae_mm, 2), fixed(m2.bias_mm, 2)]);
  const event = panel.getByRole("table", { name: /CSI for E1 heavy district events, pooled/ });
  const csi = (await event.locator("tbody tr").first().locator("td").allTextContents()).map((c) => c.trim());
  expect(csi).toEqual(["M0", "M1", "M2", "M3", "M4"].map((m) => fixed(api.categorical.E1.heavy.pooled.all[m].CSI, 3)));
});

test("definition, threshold, metric and breakdown toggles re-render with groups and undefined values preserved", async ({ page }) => {
  const api = await (await page.request.get("/api/science/evidence/district-verification?year=2025")).json();
  const panel = await openTab(page);
  await panel.getByRole("button", { name: /^E2 ≥ 25 % of valid area/ }).click();
  await panel.getByRole("button", { name: "Very Heavy ≥ 115.6 mm / 24 h" }).click();
  await panel.getByRole("button", { name: "FAR", exact: true }).click();
  const table = panel.getByRole("table", { name: /FAR for E2 very heavy district events, pooled/ });
  const far = (await table.locator("tbody tr").first().locator("td").allTextContents()).map((c) => c.trim());
  expect(far).toEqual(["M0", "M1", "M2", "M3", "M4"].map((m) => fixed(api.categorical.E2.very_heavy.pooled.all[m].FAR, 3)));
  expect(far[2]).toBe("undefined");                                      // M2 forecasts no event: undefined, never 0
  await panel.getByRole("button", { name: "By latitude band" }).click();
  await expect(panel.getByRole("table", { name: /by latitude band/i }).locator("tbody tr")).toHaveCount(3);
  await panel.getByRole("button", { name: "By lead day" }).click();
  await expect(panel.getByRole("table", { name: /by lead day/i }).locator("tbody tr")).toHaveCount(3);
  await panel.getByRole("button", { name: "By pseudo-regime" }).click();
  await expect(panel.getByRole("table", { name: /by pseudo-regime/i }).locator("tbody tr")).toHaveCount(3);
});

test("paired contrasts and improved/worsened counts carry denominators and the expected-by-chance caveat", async ({ page }) => {
  const api = await (await page.request.get("/api/science/evidence/district-verification?year=2025")).json();
  const panel = await openTab(page);
  const contrasts = panel.getByRole("table", { name: /Paired whole-case bootstrap differences in district-event CSI/ });
  await expect(contrasts.locator("tbody tr")).toHaveCount(7);
  await expect(contrasts).toContainText(/interval (excludes|includes) 0/);
  const counts = panel.getByRole("table", { name: /improved, worsened or indeterminate versus Raw/ });
  const m3 = api.improved_worsened.M3;
  const row = (await counts.locator("tbody tr").nth(2).locator("td").allTextContents()).map((c) => c.trim());
  expect(row).toEqual([String(m3.tested_districts), String(m3.improved), String(m3.worsened), String(m3.indeterminate), `${m3.expected_by_chance_total} / ${m3.expected_by_chance_per_direction}`]);
  await expect(panel.getByText(/about 5 % in total would be classified improved or worsened by chance/)).toBeVisible();
});

test("the district table gates per-district scores on support and the map is ready", async ({ page }) => {
  const api = await (await page.request.get("/api/science/evidence/district-verification?year=2025")).json();
  const panel = await openTab(page);
  const table = panel.getByRole("table", { name: /Per-district mean improvement versus Raw/ });
  await expect(table.locator("tbody tr")).toHaveCount(169);
  await expect(table.locator("tbody tr", { hasText: "insufficient support" }).first()).toBeVisible();
  await panel.getByLabel(/Only districts with ≥ 30 observed heavy events/).check();
  await expect(table.locator("tbody tr")).toHaveCount(api.supported_district_counts.E1.heavy);
  await expect(table.locator("tbody tr").first()).not.toContainText("insufficient support");
  await expect(panel.locator(".district-map[data-ready='true']")).toHaveCount(1);
  await expect(panel.getByRole("img", { name: /Diverging scale: warm colours mean the corrected district mean is farther from IMD than Raw/ })).toBeVisible();
  await expect(panel.getByText(/districts excluded for coverage/).first()).toBeVisible();
});

test("2024 is labelled development evidence and the reports download with label and protocol hash", async ({ page }) => {
  const panel = await openTab(page);
  await page.getByRole("combobox", { name: /^Year/ }).selectOption("2024");
  await expect(panel.getByText(/2024 validation\/selection year: development evidence/)).toBeVisible();
  const [download] = await Promise.all([page.waitForEvent("download"), panel.getByRole("link", { name: "Markdown", exact: true }).click()]);
  expect(download.suggestedFilename()).toBe("varshasetu_district_verification_B_2024.md");
  const markdown = readFileSync((await download.path())!, "utf8");
  expect(markdown).toContain("development evidence");
  expect(markdown).toContain("9b348063a6ac654e88a822694fd199d2f432d5d6b0bebafc19567f6be6e53365");
  expect(markdown).toContain("Expected by chance");
  const [csv] = await Promise.all([page.waitForEvent("download"), panel.getByRole("link", { name: "CSV", exact: true }).click()]);
  expect(readFileSync((await csv.path())!, "utf8").split("\n")[0]).toBe("year,evidence_role,district_id,district_name,region,included_cases,model,kind,definition,threshold,metric,value,note");
});

test("the Districts page links to district-level verification and the tab does not overflow small screens", async ({ page }) => {
  await page.goto("/districts?experiment=operational&year=2025");
  await expect(page.getByRole("link", { name: /Verification Lab → District-level tab/ })).toHaveAttribute("href", "/verification");
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 844 });
    await openTab(page);
    const dimensions = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(dimensions.page, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(dimensions.viewport + 1);
  }
});
