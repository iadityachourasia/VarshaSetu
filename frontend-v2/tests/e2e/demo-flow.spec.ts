import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("official historical demo path is backed by frozen science", async ({ page }) => {
  const comparison = await (await page.request.get("/api/science/model-comparison")).json();
  const rawRmse = comparison.results.M0_RAW_GEFS.overall.continuous.rmse_mm;
  const correctedRmse = comparison.results.M2_GLOBAL_XGBOOST.overall.continuous.rmse_mm;
  const expectedReduction = ((rawRmse - correctedRmse) / rawRmse * 100).toFixed(2);
  const catalogue = await (await page.request.get("/api/science/demo-cases")).json();
  const primary = "20190802T000000Z_day3_24h";
  expect(catalogue.cases.some((item: { case_id: string }) => item.case_id === primary)).toBe(true);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "VarshaSetu" })).toBeVisible();
  await expect(page.getByText(expectedReduction + "%", { exact: true })).toBeVisible();
  await expect(page.getByText(/2019 GEFSv12 reforecast/i).first()).toBeVisible();
  await page.getByRole("link", { name: /Explore 2019 forecast intelligence/i }).click();
  await expect(page.getByRole("heading", { name: "Forecast Explorer" })).toBeVisible();
  await expect(page).toHaveURL(new RegExp(primary));
  await expect(page.getByRole("region", { name: "Raw GEFS map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "VarshaSetu Corrected map" })).toBeVisible();
  await expect(page.getByRole("region", { name: "IMD Observed map" })).toBeVisible();
  await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
  await expect.poll(async () => page.locator(".map-canvas").evaluateAll((nodes) => {
    const cameras = nodes.map((node) => (node as HTMLElement).dataset.camera);
    return cameras.every(Boolean) && new Set(cameras).size === 1;
  })).toBe(true);
  const rawMap = page.getByRole("region", { name: "Raw GEFS map" }).locator(".map-canvas");
  const box = await rawMap.boundingBox();
  if (!box) throw new Error("Raw map has no visible bounds");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 35, box.y + box.height / 2 + 18, { steps: 6 });
  await page.mouse.up();
  await expect.poll(async () => page.locator(".map-canvas").evaluateAll((nodes) => new Set(nodes.map((node) => (node as HTMLElement).dataset.camera)).size)).toBe(1);
  await page.getByLabel("Latitude row").selectOption("24");
  await page.getByLabel("Longitude column").selectOption("24");
  await expect(page.getByText("Correction Δ")).toBeVisible();
  await expect(page.getByText("Active Monsoon", { exact: true }).first()).toBeVisible();
  await page.getByRole("link", { name: "Extreme Rain" }).click();
  await expect(page.getByRole("heading", { name: "Extreme Rain" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Heavy rainfall probability map" })).toBeVisible();
  await page.getByRole("button", { name: /Very Heavy ·/ }).click();
  await expect(page.getByRole("region", { name: "Very-heavy rainfall probability map" })).toBeVisible();
  await page.getByRole("link", { name: "District Intelligence" }).click();
  await expect(page.getByRole("heading", { name: "District Intelligence" })).toBeVisible();
  await expect(page.getByRole("table", { name: /Area-weighted district rainfall/ })).toBeVisible();
  const districtName = await page.locator(".district-table tbody th button").first().textContent();
  await page.locator(".district-table tbody th button").first().click();
  await expect(page.locator(".district-detail h2")).toHaveText(districtName ?? "");
  await page.getByRole("link", { name: "Verification" }).click();
  await expect(page.getByText("9.73% lower RMSE")).toBeVisible();
  await expect(page.getByRole("heading", { name: "2025 operational-era historical benchmark" })).toBeVisible();
  await expect(page.getByText("3.66%", { exact: true })).toBeVisible();
  await expect(page.getByText(/Raw GEFS retained stronger heavy and very-heavy spatial FSS/)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Fractions Skill Score" })).toBeVisible();
  await page.getByRole("link", { name: "Methodology" }).click();
  await expect(page.getByText("2019", { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/primary M2 Global XGBoost correction uses no regime inputs/)).toBeVisible();
  expect(errors).toEqual([]);
});

test("critical accessibility and responsive layout", async ({ page }, testInfo) => {
  for (const [width, height] of [[1920, 1080], [1440, 900], [1366, 768], [834, 1112], [390, 844]]) {
    await page.setViewportSize({ width, height });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "VarshaSetu" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `horizontal overflow at ${width}×${height}`).toBeLessThanOrEqual(1);
    await page.screenshot({ path: testInfo.outputPath(`overview-${width}x${height}.png`), fullPage: true });
    if (width === 390) {
      await page.goto("/forecast");
      await expect(page.getByLabel("Demo cases")).toBeVisible();
      await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(1);
      await expect(page.getByRole("region", { name: "VarshaSetu Corrected map" })).toBeVisible();
      await page.getByRole("button", { name: "Raw GEFS", exact: true }).click();
      await expect(page.getByRole("region", { name: "Raw GEFS map" })).toBeVisible();
      await page.getByRole("button", { name: "IMD Observed", exact: true }).click();
      await expect(page.getByRole("region", { name: "IMD Observed map" })).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath("forecast-390x844.png"), fullPage: true });
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/verification");
  const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(scan.violations.filter((item) => ["critical", "serious"].includes(item.impact ?? ""))).toEqual([]);
});

test("all six scientific views fit video resolutions and preserve light-theme readability", async ({ page }, testInfo) => {
  const routes = ["/", "/forecast", "/extremes", "/districts", "/verification", "/methodology"];
  for (const [width, height] of [[1440, 900], [1920, 1080], [1366, 768]]) {
    await page.setViewportSize({ width, height });
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      if (route === "/forecast") await expect(page.getByRole("region", { name: "IMD Observed map" })).toBeVisible();
      if (route === "/extremes") await expect(page.getByRole("region", { name: "Heavy rainfall probability map" })).toBeVisible();
      if (route === "/districts") await expect(page.getByRole("table", { name: /Area-weighted district rainfall/ })).toBeVisible();
      if (route === "/forecast") await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
      if (route === "/extremes") await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(1);
      if (route === "/districts") await expect(page.locator(".district-map[data-ready='true']")).toHaveCount(1);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow, `${route} horizontal overflow at ${width}×${height}`).toBeLessThanOrEqual(1);
      await page.screenshot({ path: testInfo.outputPath(`${route === "/" ? "overview" : route.slice(1)}-${width}x${height}.png`), fullPage: true });
    }
  }
  await page.getByRole("button", { name: "Use light theme" }).click();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await page.screenshot({ path: testInfo.outputPath("methodology-light-1366x768.png"), fullPage: true });
});
