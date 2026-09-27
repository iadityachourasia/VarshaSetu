import { expect, test } from "@playwright/test";

test("full sidebar stays labeled at judge desktop widths", async ({ page }) => {
  for (const width of [1280, 1366, 1440]) {
    await page.setViewportSize({ width, height: 768 });
    await page.goto("/forecast?experiment=operational&year=2025");
    const geometry = await page.evaluate(() => {
      const rail = document.querySelector(".sidebar")!.getBoundingClientRect();
      const labels = [...document.querySelectorAll<HTMLElement>(".nav-group-label")];
      return { railRight: rail.right, labelsVisible: labels.some((label) => getComputedStyle(label).display !== "none"), scrollWidth: document.documentElement.scrollWidth };
    });
    expect(geometry.labelsVisible, `section labels at ${width}px`).toBe(true);
    expect(geometry.railRight, `sidebar width at ${width}px`).toBeGreaterThan(240);
    expect(geometry.scrollWidth, `document overflow at ${width}px`).toBeLessThanOrEqual(width);
  }
});

test("mobile navigation drawer opens, closes with Escape, and returns focus", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/forecast?experiment=operational&year=2025");
  const toggle = page.getByRole("button", { name: "Open navigation" });
  await expect(toggle).toHaveAttribute("aria-expanded", "false");
  await toggle.click();
  await expect(toggle).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("dialog", { name: "Mobile navigation" })).toBeVisible();
  await expect(page.getByRole("dialog").getByRole("link", { name: "Verification Lab" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Mobile navigation" })).toHaveCount(0);
  await expect(toggle).toBeFocused();
});

test("overview benchmark and evidence have structured cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".phase5-benchmark-pair article")).toHaveCount(2);
  await expect(page.locator(".phase5-status-grid > span")).toHaveCount(6);
  const cards = await page.locator(".phase5-benchmark-pair article").evaluateAll((items) => items.map((item) => ({
    background: getComputedStyle(item).backgroundColor,
    padding: getComputedStyle(item).paddingLeft,
    columns: item.querySelectorAll("dl > div").length,
  })));
  expect(cards.every((card) => card.background !== "rgba(0, 0, 0, 0)" && parseFloat(card.padding) >= 16 && card.columns === 3)).toBe(true);
  const evidence = await page.locator(".phase5-status-grid > span").evaluateAll((items) => items.every((item) => parseFloat(getComputedStyle(item).paddingLeft) >= 12));
  expect(evidence).toBe(true);
});
