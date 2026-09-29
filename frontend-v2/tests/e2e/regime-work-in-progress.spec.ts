import { expect, test } from "@playwright/test";

test("reforecast regime entry presents its full-page development state", async ({ page }) => {
  for (const width of [390, 820, 1440]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/regimes");
    await expect(page.getByRole("heading", { level: 1, name: "Feature in Development" })).toBeVisible();
    await expect(page.locator(".regime-development-stage > p")).toHaveText("This capability is currently under development and will be introduced to VarshaSetu in a forthcoming release. Further details will be announced as the feature becomes available.");
    await expect(page.getByText("Data unavailable")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Return to overview" })).toHaveAttribute("href", "/");
    const dimensions = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth, stage: document.querySelector(".regime-development-page")!.getBoundingClientRect().height }));
    expect(dimensions.page, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(dimensions.viewport + 1);
    expect(dimensions.stage, `full-page treatment at ${width}px`).toBeGreaterThanOrEqual(650);
  }
});
