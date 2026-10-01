import { readFileSync } from "node:fs";
import { expect, test, type Locator, type Page } from "@playwright/test";

// Verification Lab: regime-aware tab (Track B), Track A regime-aware section, and the exportable verification
// report (PS expected output #5). Real backend, real hash-verified evidence.

async function downloadOf(page: Page, linkName: string, scope?: Locator) {
  const link = (scope ?? page.locator(".regime-evidence").first()).getByRole("link", { name: linkName, exact: true });
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  const path = await download.path();
  return { filename: download.suggestedFilename(), text: readFileSync(path, "utf8") };
}

test("Verification page has a Track A regime-aware section with a downloadable report", async ({ page }) => {
  await page.goto("/verification");
  await expect(page.getByRole("heading", { name: /Regime-aware verification · 2018 \/ 2019 reforecast/ })).toBeVisible();
  const panel = page.locator(".regime-evidence").first();
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST")).toBeVisible();
  await expect(panel.getByText(/RMSE, MAE, bias, POD, FAR, CSI, ETS and FSS by regime and lead/)).toBeVisible();
  for (const [name, format] of [["Markdown", "md"], ["CSV", "csv"], ["JSON", "json"]] as const) {
    await expect(panel.getByRole("link", { name, exact: true })).toHaveAttribute("href", `/api/science/evidence/report?track=A&year=2019&format=${format}`);
  }
  const markdown = await downloadOf(page, "Markdown");
  expect(markdown.filename).toBe("varshasetu_verification_A_2019.md");
  expect(markdown.text).toContain("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2019 FINAL TEST");
  for (const metric of ["RMSE (mm)", "POD", "FAR", "CSI", "ETS", "FSS 3x3"]) expect(markdown.text).toContain(metric);
  const csv = await downloadOf(page, "CSV");
  expect(csv.filename).toBe("varshasetu_verification_A_2019.csv");
  expect(csv.text.split("\n")[0]).toBe("track,year,evidence_role,group_type,group,case_count,model,threshold,metric,scale,value,defined_cases,note");
});

test("switching the Track A population to 2018 relabels the evidence as development evidence", async ({ page }) => {
  await page.goto("/verification");
  await page.getByRole("combobox", { name: /^Population/ }).selectOption("2018");
  const panel = page.locator(".regime-evidence").first();
  await expect(panel.getByText(/2018 validation year: development evidence/)).toBeVisible();
  await expect(panel.getByRole("link", { name: "Markdown", exact: true })).toHaveAttribute("href", /track=A&year=2018&format=md/);
});

test("Track B Verification Lab has a Regime-aware tab for 2024 and 2025 with labelled evidence and report", async ({ page }) => {
  await page.goto("/verification");
  await page.getByRole("tab", { name: "Regime-aware" }).click();
  const panel = page.locator('[role="tabpanel"] .regime-evidence');
  await expect(panel.getByText("POST-HOC EXPLORATORY ANALYSIS OF THE COMPLETED 2025 FINAL TEST")).toBeVisible();
  await expect(panel.getByRole("table", { name: "CSI by forecast-only pseudo-regime" })).toBeVisible();
  await page.getByRole("combobox", { name: /^Year/ }).selectOption("2024");
  await expect(panel.getByText(/2024 validation\/selection year: development evidence/)).toBeVisible();
  await expect(panel.getByRole("link", { name: "CSV", exact: true })).toHaveAttribute("href", /track=B&year=2024&format=csv/);
  const report = await downloadOf(page, "JSON", panel);
  expect(report.filename).toBe("varshasetu_verification_B_2024.json");
  const body = JSON.parse(report.text);
  expect(body.schema).toBe("varshasetu-verification-report-v1");
  expect(body.evidence_label).toContain("development evidence");
  expect(body.rows.length).toBeGreaterThan(1000);
});

test("the Regime page offers the same report downloads", async ({ page }) => {
  await page.goto("/regimes?experiment=operational&year=2025");
  await expect(page.locator(".regime-evidence").getByRole("link", { name: "Markdown", exact: true })).toHaveAttribute("href", /track=B&year=2025&format=md/);
});

test("regime-aware verification does not overflow phone and tablet widths", async ({ page }) => {
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/verification");
    await expect(page.locator(".regime-evidence").first()).toBeVisible();
    const dimensions = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(dimensions.page, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(dimensions.viewport + 1);
  }
});
