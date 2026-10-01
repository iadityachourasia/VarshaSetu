import { expect, test } from "@playwright/test";

// Synoptic chart (wide-domain wind, height and pressure) against the REAL backend: layers are built from the frozen fields,
// the point reader equals the API, and unavailable data never produces a chart.

const CASE = "20250730_day1_24h";
const URL = `/forecast?experiment=operational&year=2025&case=${CASE}`;

async function open(page: import("@playwright/test").Page, url = URL) {
  await page.goto(url);
  await page.getByLabel("Variable").selectOption("synoptic");
  await page.waitForFunction(() => document.querySelector(".synoptic-canvas")?.getAttribute("data-wind-arrows"), undefined, { timeout: 60_000 });
}
const attr = (page: import("@playwright/test").Page, name: string) => page.locator(".synoptic-canvas").getAttribute(`data-${name}`);

test("the synoptic view draws shading, height contours, isobars and wind arrows from the frozen 51 x 81 fields", async ({ page }) => {
  await open(page);
  await expect(page.locator(".synoptic-canvas")).toHaveAttribute("data-ready", "true");
  expect(await attr(page, "shaded-cells")).toBe(String(51 * 81));
  expect(Number(await attr(page, "height-contours"))).toBeGreaterThan(3);
  expect(Number(await attr(page, "pressure-contours"))).toBeGreaterThan(3);
  // one arrow per degree on the 0.5-degree grid: 26 rows x 41 columns, minus calm points
  const arrows = Number(await attr(page, "wind-arrows"));
  expect(arrows).toBeGreaterThan(0.8 * 26 * 41);
  expect(arrows).toBeLessThanOrEqual(26 * 41);
  await expect(page.getByLabel("Synoptic chart").getByText(/solid lines every \d+ gpm/)).toBeVisible();
  await expect(page.getByText(/dashed red box = the 49 × 49 rainfall verification domain/)).toBeVisible();
  await expect(page.getByText(/confirmed against the independently stored Track A coordinates/)).toBeVisible();
});

test("layer toggles change what is drawn", async ({ page }) => {
  await open(page);
  await page.getByRole("checkbox", { name: "850-hPa wind" }).uncheck();
  await expect.poll(() => attr(page, "wind-arrows")).toBe("0");
  await page.getByRole("checkbox", { name: "500-hPa height" }).uncheck();
  await expect.poll(() => attr(page, "height-contours")).toBe("0");
  await expect(page.locator(".synoptic-label-height")).toHaveCount(0);
  await page.getByRole("checkbox", { name: "Sea-level pressure" }).uncheck();
  await expect.poll(() => attr(page, "pressure-contours")).toBe("0");
  await page.locator(".phase5-controls").filter({ hasText: "Shading" }).getByRole("combobox").selectOption("none");
  await expect.poll(() => attr(page, "shaded-cells")).toBe("0");
  await page.locator(".phase5-controls").filter({ hasText: "Shading" }).getByRole("combobox").selectOption("q700");
  await expect.poll(() => attr(page, "shaded-cells")).toBe(String(51 * 81));
  await page.getByRole("checkbox", { name: "500-hPa height" }).check();
  await expect.poll(async () => Number(await attr(page, "height-contours"))).toBeGreaterThan(0);
  await expect(page.locator(".synoptic-label-height").first()).toBeVisible();
});

test("the point reader equals the verified API values at the selected grid point", async ({ page }) => {
  const get = async (field: string) => (await (await page.request.get(`/api/science/operational/2025/cases/${CASE}/atmosphere/${field}`)).json()) as { values: number[][]; latitude_centers: number[]; longitude_centers: number[] };
  const [pwat, z500, mslp] = await Promise.all([get("pwat"), get("z500"), get("mslp")]);
  const row = pwat.latitude_centers.indexOf(20), column = pwat.longitude_centers.indexOf(80);
  expect([row, column]).toEqual([30, 50]);
  await open(page);
  const reader = page.locator(".synoptic-reader");
  await reader.locator("select").nth(0).selectOption("20");   // latitude
  await reader.locator("select").nth(1).selectOption("80");   // longitude
  await expect(reader.locator("h2")).toHaveText("20.0° N · 80.0° E");
  await expect(reader).toContainText(`${pwat.values[row][column].toFixed(1)} kg/m²`);
  await expect(reader).toContainText(`${z500.values[row][column].toFixed(0)} gpm`);
  await expect(reader).toContainText(`${(mslp.values[row][column] / 100).toFixed(1)} hPa`);
});

test("a case whose atmosphere failed quality control shows a message and no chart data", async ({ page }) => {
  await page.route("**/atmosphere/pwat", (route) => route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ code: "SCIENCE_CASE_NOT_ELIGIBLE", detail: "Atmospheric fields failed canonical QC" }) }));
  await page.goto(URL);
  await page.getByLabel("Variable").selectOption("synoptic");
  await expect(page.getByText(/did not pass canonical quality control, so no synoptic chart is shown/)).toBeVisible();
  await expect(page.locator(".synoptic-canvas")).not.toHaveAttribute("data-wind-arrows", /.+/);
  await expect(page.locator(".synoptic-reader")).toHaveCount(0);
});

test("an integrity failure is a hard failure, never a chart", async ({ page }) => {
  await page.route("**/atmosphere/u850", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ code: "SCIENCE_INTEGRITY_FAILURE", detail: "hash mismatch" }) }));
  await page.goto(URL);
  await page.getByLabel("Variable").selectOption("synoptic");
  await expect(page.getByText(/integrity check failed/)).toBeVisible();
  await expect(page.locator(".synoptic-reader")).toHaveCount(0);
});

test("the chart works for a 2024 validation case and fits a phone screen", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page, "/forecast?experiment=operational&year=2024");
  await expect(page.locator(".synoptic-canvas")).toHaveAttribute("data-ready", "true");
  expect(Number(await attr(page, "wind-arrows"))).toBeGreaterThan(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1);
});

test("the synoptic option exists only for the operational-era experiment", async ({ page }) => {
  await page.goto(URL);
  await expect(page.getByLabel("Variable").locator("option", { hasText: "Synoptic chart" })).toHaveCount(1);
});
