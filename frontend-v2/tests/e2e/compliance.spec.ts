import { expect, test } from "@playwright/test";
import { COMPLIANCE_HIDDEN_REASON, COMPLIANCE_PAGE } from "./helpers/features";

test.skip(!COMPLIANCE_PAGE, COMPLIANCE_HIDDEN_REASON);

// SIH26080 requirement-coverage page against the REAL backend: honest statuses, evidence-resolved values,
// and every link on the page must lead to a working page (2-3 click reachability for each requirement).

type Row = { id: string; status: string; requirement: string; pages: { label: string; href: string }[]; facts: { label: string; value: number; format: string }[] };

async function coverage(page: import("@playwright/test").Page) {
  const response = await page.request.get("/api/science/evidence/ps-coverage");
  expect(response.ok()).toBeTruthy();
  return response.json() as Promise<{ counts: Record<string, number>; mandatory_counts: Record<string, number>; rows: Row[] }>;
}

test("the compliance page lists every requirement with an honest status and API-derived counts", async ({ page }) => {
  const api = await coverage(page);
  await page.goto("/compliance");
  await expect(page.getByRole("heading", { level: 1, name: "SIH26080 Requirement Coverage" })).toBeVisible();
  const mandatory = Object.values(api.mandatory_counts).reduce((a, b) => a + b, 0);
  for (const [status, label] of [["IMPLEMENTED", "Implemented"], ["PARTIAL", "Partial"], ["PLANNED", "Planned"]] as const) {
    await expect(page.getByLabel("Coverage summary").getByText(`${api.counts[status]} of ${api.rows.length} rows · ${api.mandatory_counts[status]} of ${mandatory} mandatory`)).toBeVisible();
    expect(label.length).toBeGreaterThan(0);
  }
  await expect(page.locator(".coverage-table tbody tr")).toHaveCount(api.rows.length);
  const wd = api.rows.find((r) => r.id === "REGIME-WESTERN-DISTURBANCE")!;
  const wdRow = page.locator(".coverage-table tbody tr", { hasText: wd.requirement });
  // western disturbance is IMPLEMENTED only through the sealed-year detection verdict, and the row says what that does not mean
  await expect(wdRow.locator(".coverage-status")).toHaveText("Implemented");
  await expect(wdRow.locator(".phase5-caveat")).toContainText("largely verifies the forecast height field");
  await expect(wdRow.getByRole("link", { name: "Regime Intelligence (sealed-year regime detection)" }).first()).toHaveAttribute("href", "/regimes");
  // coastal/orographic is IMPLEMENTED through the sealed-year detector; there is still no specialist rainfall model and the row says so
  const coastal = api.rows.find((r) => r.id === "REGIME-COASTAL-OROGRAPHIC")!;
  const coastalRow = page.locator(".coverage-table tbody tr", { hasText: coastal.requirement });
  await expect(coastalRow.locator(".coverage-status")).toHaveText("Implemented");
  await expect(coastalRow.locator(".phase5-caveat")).toContainText("no specialist rainfall model");
  await expect(coastalRow.getByRole("link", { name: "Geographic Zones" })).toHaveAttribute("href", "/zones");
  const classifier = page.locator(".coverage-table tbody tr", { hasText: "Weather-regime classifier" }).first();
  await expect(classifier.locator(".coverage-status")).toHaveText("Implemented");
});

test("figures on the page equal the evidence-resolved API values and post-hoc years are labelled", async ({ page }) => {
  const api = await coverage(page);
  await page.goto("/compliance");
  const far = api.rows.find((r) => r.id === "METRIC-FAR")!;
  const m3 = far.facts.find((f) => f.label.includes("M3"))!;
  const tr = page.locator(".coverage-table tbody tr", { hasText: "FAR (false alarm ratio)" });
  await expect(tr.locator(".coverage-facts li", { hasText: m3.label })).toContainText(m3.value.toFixed(3));
  await expect(tr.getByText(/post-hoc analysis of a completed final test/).first()).toBeVisible();
  const rmse = api.rows.find((r) => r.id === "METRIC-RMSE")!;
  const rmseRow = page.locator(".coverage-table tbody tr").filter({ has: page.locator("th strong", { hasText: /^RMSE$/ }) });
  await expect(rmseRow.locator(".coverage-facts")).toContainText(rmse.facts[0].value.toFixed(2));
});

test("the status filter narrows the table and keeps planned items visible on request", async ({ page }) => {
  const api = await coverage(page);
  await page.goto("/compliance");
  await page.getByRole("button", { name: "Planned", exact: true }).click();
  await expect(page.locator(".coverage-table tbody tr")).toHaveCount(api.counts.PLANNED);
  await page.getByRole("button", { name: "Partial", exact: true }).click();
  await expect(page.locator(".coverage-table tbody tr")).toHaveCount(api.counts.PARTIAL);
  await page.getByRole("button", { name: "All rows" }).click();
  await expect(page.locator(".coverage-table tbody tr")).toHaveCount(api.rows.length);
});

test("every page link on the compliance page leads to a working page (one click from the page)", async ({ page }) => {
  const api = await coverage(page);
  const hrefs = [...new Set(api.rows.flatMap((r) => r.pages.map((p) => p.href)))];
  expect(hrefs.length).toBeGreaterThanOrEqual(10);
  await page.goto("/compliance");
  for (const href of hrefs) {
    await expect(page.locator(`.coverage-table a[href="${href}"]`).first()).toBeVisible();
  }
  for (const href of hrefs) {
    const response = await page.goto(href);
    expect(response?.status(), href).toBeLessThan(400);
    await expect(page.locator("h1").first(), href).toBeVisible();
    await expect(page.getByText("Data unavailable"), href).toHaveCount(0);
  }
});

test("the sidebar links to compliance and the page does not overflow narrow screens", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "SIH26080 Compliance" }).first().click();
  await expect(page).toHaveURL(/\/compliance$/);
  for (const width of [390, 820]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/compliance");
    await expect(page.locator(".coverage-table").first()).toBeVisible();
    const dimensions = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(dimensions.page, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(dimensions.viewport + 1);
  }
});
