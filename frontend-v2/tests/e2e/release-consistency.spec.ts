import { expect, test } from "@playwright/test";
import { BASEMAP_SKIP_REASON, basemapReachable } from "./helpers/online";

const primary = "20190802T000000Z_day3_24h";
const casePath = "/api/science/cases/" + primary;

test("scientific display is consistent with the frozen API", async ({ page, request }) => {
  const [status, caseDetail, rainfall, probabilities] = await Promise.all([
    request.get("/api/science/status").then((r) => r.json()),
    request.get(casePath).then((r) => r.json()),
    request.get(casePath + "/rainfall").then((r) => r.json()),
    request.get(casePath + "/probabilities").then((r) => r.json()),
  ]);
  expect(status.readiness_state).toBe("prototype_scientific_ready");
  expect(status.operational_ready).toBe(false);
  expect(probabilities.data.thresholds_mm_24h).toEqual({ heavy: 64.5, very_heavy: 115.6 });
  expect(rainfall.initialization_utc).toBe(caseDetail.initialization_utc);
  expect(probabilities.valid_period_end_utc).toBe(caseDetail.valid_period_end_utc);

  await page.goto("/forecast?case=" + primary);
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect(page.getByText("Historical scientific prototype · not operational")).toBeVisible();
  const legends = await page.locator('.legend[aria-label="Shared rainfall legend, millimeters per 24 hours"]').count();
  expect(legends).toBe(1);
  const row = Number(await page.getByLabel("Latitude row").inputValue());
  const column = Number(await page.getByLabel("Longitude column").inputValue());
  expect(rainfall.data.valid_mask[row][column]).toBe(true);
  const inspected = await page.locator(".inspection-panel .cell-values").innerText();
  expect(inspected).toContain(rainfall.data.raw[row][column].toFixed(1) + " mm");
  expect(inspected).toContain(rainfall.data.corrected[row][column].toFixed(1) + " mm");
  expect(inspected).toContain(rainfall.data.observed[row][column].toFixed(1) + " mm");
  expect(inspected).not.toContain("Unavailable");
  await page.goto("/extremes?case=" + primary);
  await expect(page.getByText("Heavy · ≥64.5 mm / 24 h")).toBeVisible();
  await expect(page.getByText("Very Heavy · ≥115.6 mm / 24 h")).toBeVisible();
  expect(Number(await page.getByLabel("Latitude row").inputValue())).toBe(row);
  expect(Number(await page.getByLabel("Longitude column").inputValue())).toBe(column);
  await page.getByRole("button", { name: /Very Heavy ·/ }).click();
  await expect(page.getByText(/Probability is calibrated forecast likelihood, not rainfall amount/)).toBeVisible();
});

test("online vector geography loads from the official provider", async ({ page }) => {
  test.skip(!(await basemapReachable()), BASEMAP_SKIP_REASON);
  const tiles: number[] = [];
  const missingSprites: string[] = [];
  page.on("console", (message) => { if (message.text().includes('Image "circle-11" could not be loaded')) missingSprites.push(message.text()); });
  page.on("response", (response) => {
    if (response.url().startsWith("https://tiles.openfreemap.org/planet/") && response.url().endsWith(".pbf")) tiles.push(response.status());
  });
  await page.goto("/forecast?case=" + primary);
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect.poll(() => tiles.filter((status) => status === 200).length, { timeout: 25_000 }).toBeGreaterThan(0);
  await expect(page.getByText(/OpenFreeMap.*OpenMapTiles/).first()).toBeVisible();
  await expect(page.getByText("Offline geography")).toHaveCount(0);
  expect(missingSprites).toEqual([]);
});

test("offline style failure leaves local science and district interaction usable", async ({ page }) => {
  await page.route("https://tiles.openfreemap.org/**", (route) => route.abort());
  await page.goto("/forecast?case=" + primary);
  await expect(page.getByText("Offline geography").first()).toBeVisible();
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect(page.locator(".inspection-panel .cell-values")).not.toContainText("Unavailable");
  await page.goto("/extremes?case=" + primary);
  await expect(page.getByText("Offline geography")).toBeVisible();
  await expect(page.getByText("Selected probability")).toBeVisible();
  await page.goto("/districts?case=" + primary);
  await expect(page.getByText("Offline geography")).toBeVisible();
  const first = page.locator(".district-table tbody th button").first();
  const name = await first.innerText();
  await first.click();
  await expect(page.locator(".district-detail h2")).toHaveText(name);
});
