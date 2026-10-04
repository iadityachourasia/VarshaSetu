import { expect, test } from "@playwright/test";
import { BASEMAP_SKIP_REASON, basemapReachable } from "./helpers/online";

test("forecast cartography controls preserve exact scientific inspection", async ({ page }, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/forecast");
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect(page.locator(".map-canvas[data-district-label-count='188']")).toHaveCount(3);
  await expect(page.getByText("Loading geography…")).toHaveCount(0);
  await page.waitForTimeout(1200);
  await page.screenshot({ path: testInfo.outputPath("forecast-dark-weather-online.png"), fullPage: true });
  await page.getByLabel("Latitude row").selectOption("24");
  await page.getByLabel("Longitude column").selectOption("24");
  const exact = (await page.locator(".inspection-panel .cell-values").textContent()) ?? "";
  await page.getByLabel("Scientific display mode").selectOption("grid");
  await expect(page.getByLabel("Scientific display mode")).toHaveValue("grid");
  await expect(page.locator(".inspection-panel .cell-values")).toHaveText(exact);
  await page.screenshot({ path: testInfo.outputPath("forecast-dark-scientific-grid-selected-cell.png"), fullPage: true });
  await page.getByLabel("Scientific overlay opacity").fill("40");
  await expect(page.locator(".opacity-control output")).toHaveText("40%");
  await page.getByLabel("Geographic map style").selectOption("light");
  await expect(page.getByLabel("Geographic map style")).toHaveValue("light");
  await expect(page.getByText("Loading geography…")).toHaveCount(0);
  await page.waitForTimeout(1200);
  await expect(page.locator(".inspection-panel .cell-values")).toHaveText(exact);
  await page.screenshot({ path: testInfo.outputPath("forecast-light-scientific-grid.png"), fullPage: true });
  await page.getByRole("button", { name: "Zoom in" }).click();
  await page.getByRole("button", { name: "Reset map extent" }).click();
  await expect.poll(async () => page.locator(".map-canvas").evaluateAll((nodes) => new Set(nodes.map((node) => (node as HTMLElement).dataset.camera)).size)).toBe(1);
  await page.getByLabel("Scientific display mode").selectOption("weather");
  await expect(page.locator(".inspection-panel .cell-values")).toHaveText(exact);
  expect(errors).toEqual([]);
});

test("district selection and online-style fallback retain local geometry", async ({ page }, testInfo) => {
  await page.route("https://tiles.openfreemap.org/**", (route) => route.abort());
  await page.goto("/districts");
  await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
  await expect(page.getByText("Offline geography")).toBeVisible();
  await expect(page.locator(".district-map[data-district-label-mode='offline-icons'][data-district-label-count='188']")).toHaveCount(1);
  const first = page.locator(".district-table tbody th button").first();
  const name = await first.innerText();
  await first.click();
  await expect(page.locator(".district-detail h2")).toHaveText(name);
  await page.screenshot({ path: testInfo.outputPath("district-offline-selected.png"), fullPage: true });
  await page.getByRole("button", { name: "Reset map extent" }).click();
  await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
  await expect.poll(async () => Number(await page.locator(".district-map").getAttribute("data-district-labels-rendered")), { timeout: 30000 }).toBeGreaterThan(1);
  await page.screenshot({ path: testInfo.outputPath("district-offline-regional-labels.png"), fullPage: true });
  // The credits are collapsed to an "i" by default and open on click.
  await page.getByRole("button", { name: "Show map data credits" }).first().click();
  await expect(page.getByText(/geoBoundaries, ODbL 1.0/).first()).toBeVisible();
});

test("district labels persist across desktop map pages and widths", async ({ page }, testInfo) => {
  test.skip(!(await basemapReachable()), BASEMAP_SKIP_REASON);
  test.setTimeout(240_000); // Nine tile/glyph-backed screenshots; allow public basemap latency.
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  for (const [width, height] of [[1920, 1080], [1440, 900], [1366, 768]]) {
    await page.setViewportSize({ width, height });
    for (const route of ["forecast", "extremes", "districts"]) {
      await page.goto(`/${route}`);
      const maps = page.locator(route === "districts" ? ".district-map" : ".map-canvas");
      await expect(maps.first()).toHaveAttribute("data-ready", "true");
      await expect(maps.first()).toHaveAttribute("data-district-label-count", "188");
      await expect(page.getByText("Loading geography…")).toHaveCount(0);
      await expect.poll(async () => Number(await maps.first().getAttribute("data-district-labels-rendered")), { timeout: 30000 }).toBeGreaterThan(0);
      if (route === "forecast" && width >= 1366) {
        await expect.poll(async () => await maps.evaluateAll((nodes) => nodes.every((node) => Number((node as HTMLElement).dataset.districtLabelsRendered) > 0)), { timeout: 30000 }).toBe(true);
      }
      await page.screenshot({ path: testInfo.outputPath(`${route}-district-labels-${width}x${height}.png`), fullPage: true });
      expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(1);
    }
  }
  expect(errors).toEqual([]);
});

test("scientific map routes fit tablet and mobile viewports", async ({ page }, testInfo) => {
  test.skip(!(await basemapReachable()), BASEMAP_SKIP_REASON);
  for (const [width, height] of [[834, 1112], [390, 844]]) {
    await page.setViewportSize({ width, height });
    for (const route of ["/forecast", "/extremes", "/districts"]) {
      await page.goto(route);
      const map = page.locator(route === "/districts" ? ".district-map[data-ready='true']" : ".map-canvas[data-ready='true']").first();
      await expect(map).toBeVisible();
      await expect.poll(async () => Number(await map.getAttribute("data-district-labels-rendered")), { timeout: 30000 }).toBeGreaterThan(0);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${route} overflow at ${width}×${height}`).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`${route.slice(1)}-${width}x${height}.png`), fullPage: true });
    }
  }
});
