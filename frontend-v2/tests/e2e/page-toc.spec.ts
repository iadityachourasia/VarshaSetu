import { expect, test } from "@playwright/test";

// The long evidence pages carry an in-page navigation; every link must resolve to an element on the page.
for (const path of ["/verification", "/regimes"]) {
  test(`${path}: every in-page navigation link points at an existing section`, async ({ page }) => {
    await page.goto(path);
    const toc = page.getByTestId("page-toc");
    await expect(toc).toBeVisible();
    const hrefs = await toc.locator("a").evaluateAll((links) => links.map((a) => a.getAttribute("href") ?? ""));
    expect(hrefs.length).toBeGreaterThanOrEqual(5);
    for (const href of hrefs) {
      expect(href.startsWith("#")).toBe(true);
      await expect(page.locator(`[id="${href.slice(1)}"]`)).toHaveCount(1);
    }
  });
}

test("the evidence tables are not trapped in a nested scroll box (only the district product table scrolls inside itself)", async ({ page }) => {
  await page.goto("/regimes");
  await expect(page.getByRole("table").first()).toBeVisible();
  const clipped = await page.locator(".district-table-wrap").evaluateAll((boxes) => boxes.filter((box) => box.scrollHeight > box.clientHeight + 1).length);
  expect(clipped).toBe(0);
});

test("the live page lists its caveats once", async ({ page }) => {
  await page.goto("/live");
  await expect(page.getByTestId("live-banner")).toBeVisible();
  await expect(page.getByText("Not an official warning and not a forecast product of any national centre.")).toHaveCount(1);
});
