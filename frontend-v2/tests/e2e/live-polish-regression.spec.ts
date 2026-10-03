import { expect, test } from "@playwright/test";

test("first visits start in light mode regardless of system preference and honor a saved choice", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");
  await expect(page.locator("html")).not.toHaveClass(/dark/);
  await expect(page.getByRole("button", { name: "Use dark theme" })).toBeVisible();
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(/dark/);
  await page.getByRole("button", { name: "Use light theme" }).click();
  await page.reload();
  await expect(page.locator("html")).not.toHaveClass(/dark/);
});

test("supplied logos match the theme across the shared brand surfaces", async ({ page }) => {
  await page.goto("/");
  const mark = page.locator(".sidebar .brand-symbol");
  await expect(mark).toBeVisible();
  await expect(mark).toHaveCSS("background-image", /varshasetu-light\.png/);
  await expect(page.locator(".header-brand-copy > a span:last-child")).toHaveCSS("color", "rgb(0, 107, 124)");
  await page.getByRole("button", { name: "Present VarshaSetu" }).click();
  await expect(page.locator(".story-identity .brand-symbol")).toHaveCSS("background-image", /varshasetu-light\.png/);
  await page.getByRole("button", { name: "Exit" }).first().click();
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(mark).toHaveCSS("background-image", /varshasetu-dark-cutout\.png/);
  await expect(mark).toHaveCSS("background-color", "rgba(0, 0, 0, 0)");
  await expect(page.locator(".header-brand-copy > a span:last-child")).toHaveCSS("color", "rgb(84, 237, 242)");
  for (const asset of ["varshasetu-light.png", "varshasetu-dark-cutout.png"]) {
    const status = await page.evaluate(async (name) => (await fetch(`/brand/${name}`)).status, asset);
    expect(status).toBe(200);
  }

  await page.getByRole("button", { name: "Use light theme" }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator(".mobile-brand-mark")).toHaveCSS("background-image", /varshasetu-light\.png/);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.locator(".drawer-brand-mark")).toHaveCSS("background-image", /varshasetu-light\.png/);
});

test("sidebar expands on hover anywhere and contracts on pointer exit", async ({ page }) => {
  for (const width of [820, 1280, 1366, 1440, 1920]) {
    await page.setViewportSize({ width, height: 768 });
    await page.goto("/");
    await expect(page.getByRole("link", { name: "Return to VarshaSetu overview" })).toBeVisible();
    await expect(page.locator(".header-context")).not.toContainText("Regime-Aware AI Post-Processing of Monsoon Rainfall Forecasts");
    const toggle = page.getByRole("button", { name: "Expand navigation" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator(".sidebar-brand-control .sidebar-brand-toggle")).toBeVisible();
    await expect(page.locator(".header-brand-logo")).toBeVisible();
    await expect(page.getByRole("button", { name: "Presentation View" })).toHaveCount(0);
    await expect(page.locator(".sidebar-toggle-logo")).toHaveCSS("opacity", "1");
    await page.locator(".sidebar .nav-link").first().hover();
    await expect(page.getByRole("button", { name: "Collapse navigation" })).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");
    await page.getByRole("button", { name: "Collapse navigation" }).hover();
    await expect(page.locator(".sidebar-toggle-icon")).toHaveCSS("opacity", "1");
    await expect(page.locator(".sidebar-toggle-logo")).toHaveCSS("opacity", "0");
    const alignment = await page.locator(".header-brandline").evaluate((row) => {
      const button = row.querySelector(".header-brand-logo")!.getBoundingClientRect();
      const brand = row.querySelector("a")!.getBoundingClientRect();
      return Math.abs(button.top + button.height / 2 - brand.top - brand.height / 2);
    });
    expect(alignment, `header logo and brand vertical alignment at ${width}px`).toBeLessThanOrEqual(1);
    const edges = await page.evaluate(() => [".global-header", ".overview-hero", ".phase5-benchmark-pair", ".overview-evidence-row"].map((selector) => {
      const rect = document.querySelector(selector)!.getBoundingClientRect();
      return { left: rect.left, right: rect.right };
    }));
    expect(Math.max(...edges.map((edge) => edge.left)) - Math.min(...edges.map((edge) => edge.left)), `left edges at ${width}px`).toBeLessThanOrEqual(1);
    expect(Math.max(...edges.map((edge) => edge.right)) - Math.min(...edges.map((edge) => edge.right)), `right edges at ${width}px`).toBeLessThanOrEqual(1);
    if (width >= 1280) await expect(page.locator(".global-header")).toHaveCSS("height", "64px");
    await expect(page.locator(".sidebar .nav-link").first()).toHaveAttribute("aria-label", "Overview");
    await expect(page.locator(".sidebar-brand-name")).toBeVisible();
    await expect(page.locator(".sidebar .nav-group-label").first()).toBeVisible();
    await expect(page.locator(".sidebar .sidebar-foot-copy")).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - innerWidth);
    expect(overflow, `expanded sidebar document overflow at ${width}px`).toBeLessThanOrEqual(1);
    await page.locator(".global-header").hover();
    await expect(page.getByRole("button", { name: "Expand navigation" })).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator(".sidebar")).toHaveCSS("width", "64px");
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
  await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");
  const duration = await page.locator(".app-shell").evaluate((node) => parseFloat(getComputedStyle(node).transitionDuration));
  expect(duration).toBeLessThan(0.01);
});

test("sidebar hover also opens from its archive area", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/");
  await page.locator(".sidebar-foot-icon").hover();
  await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");
  await page.locator(".global-header").hover();
  await expect(page.locator(".sidebar")).toHaveCSS("width", "64px");
});

test("sidebar button pins either width despite subsequent hover changes", async ({ page }) => {
  for (const width of [820, 1440]) {
    await page.setViewportSize({ width, height: 768 });
    await page.goto("/");
    await page.getByRole("button", { name: "Expand navigation" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");
    await page.locator(".global-header").hover();
    await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");

    await page.getByRole("button", { name: "Collapse navigation" }).click();
    await expect(page.locator(".sidebar")).toHaveCSS("width", "64px");
    await page.locator(".global-header").hover();
    await page.locator(".sidebar .nav-link").first().hover();
    await expect(page.locator(".sidebar")).toHaveCSS("width", "64px");

    await page.getByRole("button", { name: "Expand navigation" }).click();
    await page.locator(".global-header").hover();
    await expect(page.locator(".sidebar")).toHaveCSS("width", "240px");
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

test("mobile header keeps its context and actions in two compact rows", async ({ page }) => {
  for (const width of [320, 390, 760]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    await expect(page.locator(".mobile-brand-context")).toBeVisible();
    await expect(page.locator(".mobile-brand-mark")).toBeVisible();
    const brandCenters = await page.locator(".mobile-brand-context").evaluate((row) => [
      ".mobile-brand-mark", "strong", ".mobile-brand-slash", ".mobile-brand-descriptor",
    ].map((selector) => {
      const rect = row.querySelector(selector)!.getBoundingClientRect();
      return rect.top + rect.height / 2;
    }));
    expect(Math.max(...brandCenters) - Math.min(...brandCenters), `mobile brand alignment at ${width}px`).toBeLessThanOrEqual(1);
    const controls = [
      page.getByRole("combobox", { name: "Experiment and year" }),
      page.getByRole("link", { name: "Reset Demo" }),
      page.getByRole("button", { name: "Present VarshaSetu" }),
      page.getByRole("button", { name: "Use dark theme" }),
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

test("light mobile hero veil fades into its artwork", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const background = await page.locator(".overview-main").evaluate((element) => getComputedStyle(element).backgroundImage);
  expect(background).toContain("linear-gradient(");
  expect(background).toContain("rgba(247, 252, 253, 0)");
});

test("overview benchmark and evidence have structured cards", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator(".phase5-benchmark-pair article")).toHaveCount(2);
  await expect(page.locator(".overview-evidence-row > .overview-evidence-item")).toHaveCount(6);
  await expect(page.locator(".overview-case-chart")).toHaveCount(2);
  const cards = await page.locator(".phase5-benchmark-pair article").evaluateAll((items) => items.map((item) => ({
    background: getComputedStyle(item).backgroundColor,
    padding: getComputedStyle(item).paddingLeft,
    values: item.querySelectorAll(".overview-benchmark-values > span").length,
  })));
  expect(cards.every((card) => card.background !== "rgba(0, 0, 0, 0)" && parseFloat(card.padding) >= 16 && card.values === 2)).toBe(true);
  const evidence = await page.locator(".overview-evidence-item").evaluateAll((items) => items.every((item) => parseFloat(getComputedStyle(item).paddingLeft) >= 10));
  expect(evidence).toBe(true);
});
