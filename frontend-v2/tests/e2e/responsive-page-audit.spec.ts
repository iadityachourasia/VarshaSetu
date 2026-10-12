import { expect, test } from "@playwright/test";

test("pages with independent populations do not show a misleading global year", async ({ page }) => {
  for (const route of ["/india", "/live", "/zones", "/quality", "/verification", "/observations"]) {
    await page.goto(route);
    await expect(page.getByRole("combobox", { name: "Experiment and year" })).toHaveCount(0);
  }
  await page.goto("/forecast");
  await expect(page.getByRole("combobox", { name: "Experiment and year" })).toBeVisible();
});

test("mobile scientific selectors have room for their chosen values", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [route, names] of [
    ["/forecast", ["Geographic map style", "Scientific display mode"]],
    ["/live", ["Field"]],
    ["/zones", ["Population", "Score"]],
    ["/casebook", ["Case outcome"]],
  ] as const) {
    await page.goto(route);
    for (const name of names) {
      const width = await page.getByRole("combobox", { name, exact: true }).first().evaluate((element) => element.getBoundingClientRect().width);
      expect(width, `${route}: ${name}`).toBeGreaterThan(300);
    }
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `${route} horizontal overflow`).toBeLessThanOrEqual(2);
  }
});

test("withheld live leads show a plain QC summary and retain the exact reason", async ({ page }) => {
  const status = await (await page.request.get("/api/science/live/status")).json();
  const current = status.latest_live ?? status.cycles[0];
  test.skip(!current || Object.keys(current.withheld_products).length === 0, "no withheld local lead");
  await page.goto("/live");
  const panel = page.getByTestId("live-withheld");
  await expect(panel).toContainText("quality control");
  await expect(panel).not.toContainText("ValueError:", { useInnerText: true });
  await panel.getByText("Technical QC detail").first().click();
  await expect(panel).toContainText(Object.values(current.withheld_products)[0] as string);
});

test("mobile evidence tables with their own scroll area are keyboard reachable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const route of ["/regimes", "/verification", "/india", "/live", "/zones", "/geoaware"]) {
    await page.goto(route);
    const wrappers = page.locator(".district-table-wrap");
    const count = await wrappers.count();
    for (let index = 0; index < count; index += 1) {
      const state = await wrappers.nth(index).evaluate((element) => ({
        scrollable: element.scrollWidth > element.clientWidth + 1 || element.scrollHeight > element.clientHeight + 1,
        tabIndex: element.tabIndex,
      }));
      if (state.scrollable) expect(state.tabIndex, `${route}: table ${index + 1}`).toBeGreaterThanOrEqual(0);
    }
  }
});
