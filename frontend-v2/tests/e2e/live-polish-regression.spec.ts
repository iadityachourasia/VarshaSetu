import { expect, test } from "@playwright/test";

test("sidebar starts as an icon rail and expands to labeled navigation", async ({ page }) => {
  for (const width of [820, 1280, 1366, 1440]) {
    await page.setViewportSize({ width, height: 768 });
    await page.goto("/forecast?experiment=operational&year=2025");
    await expect(page.getByRole("link", { name: "Return to VarshaSetu overview" })).toBeVisible();
    await expect(page.locator(".header-context")).not.toContainText("Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts");
    const toggle = page.getByRole("button", { name: "Expand navigation" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator(".global-header .header-brandline > .sidebar-expand-toggle")).toBeVisible();
    await expect(toggle).toHaveCSS("position", "static");
    const alignment = await page.locator(".header-brandline").evaluate((row) => {
      const button = row.querySelector("button")!.getBoundingClientRect();
      const brand = row.querySelector("a")!.getBoundingClientRect();
      return Math.abs(button.top + button.height / 2 - brand.top - brand.height / 2);
    });
    expect(alignment, `toggle and brand vertical alignment at ${width}px`).toBeLessThanOrEqual(1);
    await expect(page.locator(".sidebar")).toHaveCSS("width", "68px");
    await expect(page.locator(".sidebar .nav-link").first()).toHaveAttribute("aria-label", "Overview");
    await toggle.click();
    await expect(page.getByRole("button", { name: "Collapse navigation" })).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".sidebar")).toHaveCSS("width", "248px");
    await expect(page.locator(".sidebar .nav-group-label").first()).toBeVisible();
    await expect(page.locator(".sidebar .sidebar-foot-copy")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow, `expanded sidebar document overflow at ${width}px`).toBeLessThanOrEqual(1);
    await page.getByRole("button", { name: "Collapse navigation" }).click();
    await expect(page.locator(".sidebar")).toHaveCSS("width", "68px");
  }
});

test("sidebar toggle works by keyboard and respects reduced motion", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Expand navigation" });
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Collapse navigation" })).toBeFocused();
  await expect(page.locator(".sidebar")).toHaveCSS("width", "248px");
  const duration = await page.locator(".app-shell").evaluate((node) => parseFloat(getComputedStyle(node).transitionDuration));
  expect(duration).toBeLessThan(0.01);
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

test("mobile header keeps its context and actions in two compact rows", async ({ page }) => {
  for (const width of [320, 390, 760]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    await expect(page.locator(".mobile-brand-context")).toBeVisible();
    await expect(page.locator(".mobile-brand-mark")).toBeVisible();
    const controls = [
      page.getByRole("combobox", { name: "Experiment and year" }),
      page.getByRole("link", { name: "Reset Demo" }),
      page.getByRole("button", { name: "Presentation View" }),
      page.getByRole("button", { name: "Present VarshaSetu" }),
      page.getByRole("button", { name: "Use light theme" }),
    ];
    const boxes = await Promise.all(controls.map((control) => control.boundingBox()));
    expect(boxes.every((box) => box && box.height >= 44), `touch targets at ${width}px`).toBe(true);
    expect(new Set(boxes.map((box) => Math.round(box!.y))).size, `control rows at ${width}px`).toBe(1);
    const geometry = await page.evaluate(() => ({
      headerBottom: document.querySelector(".global-header")!.getBoundingClientRect().bottom,
      overflow: document.documentElement.scrollWidth - innerWidth,
    }));
    expect(geometry.headerBottom, `mobile chrome height at ${width}px`).toBeLessThanOrEqual(112);
    expect(geometry.overflow, `document overflow at ${width}px`).toBeLessThanOrEqual(1);
  }
});

test("overview benchmark and evidence have structured cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".phase5-benchmark-pair article")).toHaveCount(2);
  await expect(page.locator(".overview-evidence-row > .overview-evidence-item")).toHaveCount(6);
  await expect(page.locator(".overview-case-chart")).toHaveCount(2);
  const cards = await page.locator(".phase5-benchmark-pair article").evaluateAll((items) => items.map((item) => ({
    background: getComputedStyle(item).backgroundColor,
    padding: getComputedStyle(item).paddingLeft,
    values: item.querySelectorAll(".overview-benchmark-values span").length,
  })));
  expect(cards.every((card) => card.background !== "rgba(0, 0, 0, 0)" && parseFloat(card.padding) >= 16 && card.values === 2)).toBe(true);
  const evidence = await page.locator(".overview-evidence-item").evaluateAll((items) => items.every((item) => parseFloat(getComputedStyle(item).paddingLeft) >= 10));
  expect(evidence).toBe(true);
});
