import { expect, test } from "@playwright/test";

test("verification charts contain actual SVG surfaces", async ({ page }) => {
  await page.goto("/verification");
  await expect(page.locator(".chart-figure svg.recharts-surface").first()).toBeVisible();
});

test("forecast case-catalogue API failure shows a bounded error state", async ({ page }) => {
  await page.route("**/api/science/operational/2025/cases?page_size=400", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ code: "SCIENCE_PRODUCT_UNAVAILABLE", detail: "Case catalogue unavailable" }),
  }));
  await page.goto("/forecast?experiment=operational&year=2025");
  await expect(page.locator("main [role='alert']")).toContainText("case catalogue is unavailable", { timeout: 20_000 });
  await expect(page.getByRole("status", { name: "Loading verified case" })).toHaveCount(0);
});
