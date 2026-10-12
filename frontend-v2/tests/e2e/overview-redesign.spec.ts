import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("overview uses sourced benchmarks, case charts, and theme artwork", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "VarshaSetu" })).toBeVisible();
  await expect(page.locator(".overview-main .prototype-note")).toHaveCount(0);
  await expect(page.locator(".overview-footnote, .overview-probability-note")).toHaveCount(0);
  for (const removedCopy of ["2025 BSS uses fixed 2023 training prevalence", "These views serve 2019 GEFSv12", "Hero artwork is illustrative"]) {
    await expect(page.locator(".overview-page")).not.toContainText(removedCopy);
  }
  await expect(page.locator(".phase5-benchmark-pair article")).toHaveCount(2);
  await expect(page.locator(".overview-case-chart")).toHaveCount(2);
  await expect(page.locator(".overview-case-chart").first()).toContainText("2019 per-case RMSE");
  await expect(page.locator(".overview-case-chart").last()).toContainText("2025 per-case RMSE");
  await expect(page.locator(".phase5-benchmark-pair article").last()).toContainText("16.17 mm");
  for (const [index, percent] of ["9.73", "3.66"].entries()) {
    const panel = page.locator(".phase5-benchmark-pair article").nth(index);
    await expect(panel.locator(".overview-benchmark-improvement strong")).toHaveText(`${percent}%`);
    await expect(panel.locator(".overview-benchmark-improvement")).toContainText("lower aggregate RMSE");
    const prominentSize = await panel.locator(".overview-benchmark-improvement strong").evaluate((node) => parseFloat(getComputedStyle(node).fontSize));
    const rmseSize = await panel.locator(".overview-benchmark-values b").first().evaluate((node) => parseFloat(getComputedStyle(node).fontSize));
    expect(prominentSize, `${percent}% should be the largest benchmark figure`).toBeGreaterThan(rmseSize);
  }
  await expect(page.locator(".overview-benchmark-caveat")).toHaveCount(0);
  await expect(page.locator(".phase5-caveat")).toContainText("Raw GEFS retained better Heavy and Very Heavy spatial FSS");
  await expect(page.locator(".phase5-caveat")).toContainText("not pooled");
  await expect(page.locator(".overview-art-note")).toHaveCount(0);
  await expect(page.locator(".overview-page .section-heading").first()).toHaveText("Explore the 2019 evidence");
  await expect(page.locator(".capability-feature .capability-icon")).toHaveCount(3);
  await expect(page.locator(".capability-feature .capability-arrow")).toHaveCount(3);
  await expect(page.locator(".capability-feature").first()).toContainText("shared 0.25° grid");
  const features = page.getByRole("list", { name: "Implemented website features" }).locator("li");
  await expect(features).toHaveCount(6);
  await expect(features.locator("strong")).toHaveText([
    "FORECAST EXPLORER", "REGIME INTELLIGENCE", "EXTREME RAIN",
    "ENSEMBLE & UNCERTAINTY", "DISTRICT INTELLIGENCE", "VERIFICATION LAB",
  ]);
  await expect(features.nth(1)).toContainText("pseudo-regime probabilities");
  await expect(features.nth(3)).toContainText("five-member subset");
  await expect(features.nth(4)).toContainText("regional summaries");
  await expect(page.getByRole("link", { name: "Explore 2019 forecast intelligence" })).toContainText("Explore forecast intelligence");
  await expect(page.getByRole("link", { name: "View scientific validation" })).toBeVisible();
  await expect(page.locator(".overview-hero")).toHaveCSS("background-image", /hero-light\.avif/);
  await expect(page.locator(".capability-forecast")).toHaveCSS("background-image", /forecast-light\.avif/);
  await expect(page.locator(".capability-extremes")).toHaveCSS("background-image", /extremes-light\.avif/);
  await expect(page.locator(".capability-districts")).toHaveCSS("background-image", /districts-light\.avif/);
  expect(pageErrors, "initial light overview hydration").toEqual([]);
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator(".overview-hero")).toHaveCSS("background-image", /hero-dark\.avif/);
  await expect(page.locator(".capability-forecast")).toHaveCSS("background-image", /forecast-dark\.avif/);
  await expect(page.locator(".capability-extremes")).toHaveCSS("background-image", /extremes-dark\.avif/);
  await expect(page.locator(".capability-districts")).toHaveCSS("background-image", /districts-dark\.avif/);
  for (const asset of ["hero", "forecast", "extremes", "districts"]) {
    for (const theme of ["dark", "light"]) {
      const response = await page.request.get(`/overview/${asset}-${theme}.avif`);
      expect(response.ok(), `${asset}-${theme}.avif`).toBe(true);
      expect(response.headers()["content-type"]).toContain("image/avif");
    }
  }
  expect(pageErrors).toEqual([]);
});

test("all six feature tiles navigate to their implemented views", async ({ page }) => {
  for (const [title, route] of [
    ["FORECAST EXPLORER", "/forecast"],
    ["REGIME INTELLIGENCE", "/regimes"],
    ["EXTREME RAIN", "/extremes"],
    ["ENSEMBLE & UNCERTAINTY", "/ensemble"],
    ["DISTRICT INTELLIGENCE", "/districts"],
    ["VERIFICATION LAB", "/verification"],
  ]) {
    await page.goto("/");
    const link = page.getByRole("list", { name: "Implemented website features" }).getByRole("link", { name: new RegExp(title, "i") });
    await expect(link).toHaveAttribute("href", route);
    if (route === "/verification") {
      await link.focus();
      await page.keyboard.press("Enter");
    } else {
      await link.click();
    }
    await expect(page).toHaveURL((url) => url.pathname === route);
  }
});

test("shared GitHub control and homepage credits identify the project", async ({ page }) => {
  for (const width of [320, 390, 1242]) {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/");
    const github = page.getByRole("link", { name: "Open VarshaSetu GitHub repository in a new tab" });
    const theme = page.getByRole("button", { name: /Use (dark|light) theme/ });
    await expect(github).toHaveAttribute("href", "https://github.com/iadityachourasia/VarshaSetu");
    await expect(github).toHaveAttribute("target", "_blank");
    await expect(github).toBeVisible();
    const positions = await page.locator(".github-link, .theme-button").evaluateAll((nodes) => nodes.map((node) => {
      const rect = node.getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    }));
    expect(positions[0].right, `${width}px GitHub/theme order`).toBeLessThan(positions[1].left);
    expect(Math.abs(positions[0].top - positions[1].top), `${width}px control alignment`).toBeLessThanOrEqual(1);
    if (width === 320) {
      const selector = await page.getByRole("combobox", { name: "Experiment and year" }).boundingBox();
      expect(selector!.x, "320px selector left alignment").toBeLessThanOrEqual(16);
      expect(selector!.width, "320px selector width").toBeGreaterThanOrEqual(80);
    }
    await github.focus();
    await expect(github).toBeFocused();
    await expect(theme).toBeVisible();
    const credits = page.locator(".overview-credits");
    await expect(credits).toContainText("Developed by");
    await expect(credits).toContainText("TEAM METROLOGIX");
    await expect(credits).toContainText("ADITYA CHOURASIA");
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth), `${width}px document overflow`).toBeLessThanOrEqual(1);
  }
});

test("overview and shared controls remain usable across viewports", async ({ page }) => {
  for (const width of [320, 390, 820, 1366, 1440, 1920]) {
    await page.setViewportSize({ width, height: width < 1000 ? 844 : 900 });
    await page.goto("/");
    await expect(page.getByRole("link", { name: /Explore 2019 forecast intelligence/ })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Experiment and year" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Present VarshaSetu" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(1);
    if (width <= 390) {
      const height = await page.locator(".overview-hero").evaluate((element) => element.getBoundingClientRect().height);
      expect(height, `mobile hero height at ${width}px`).toBeLessThanOrEqual(width === 320 ? 650 : 620);
    }
  }
});

test("overview has no automated WCAG A/AA violations in either theme", async ({ page }) => {
  await page.goto("/");
  for (const theme of ["light", "dark"] as const) {
    const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    expect(scan.violations, theme).toEqual([]);
    if (theme === "light") await page.getByRole("button", { name: "Use dark theme" }).click();
  }
});

test("mobile drawer, chart access, and reduced transparency remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(page.getByRole("dialog", { name: "Mobile navigation" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Open navigation" })).toBeFocused();
  await page.locator(".overview-chart-viewport").first().focus();
  await expect(page.locator(".overview-chart-viewport").first()).toBeFocused();
  const client = await page.context().newCDPSession(page);
  await client.send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-transparency", value: "reduce" }] });
  await expect(page.locator(".overview-result")).toHaveCSS("backdrop-filter", "none");
  await client.detach();
});

test("historical archive card keeps its destination and theme treatment", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const archive = page.getByRole("link", { name: "Browse historical prototype cases" });
  await expect(archive).toHaveAttribute("href", "/casebook");
  await expect(archive).toContainText("2019 & 2025 cases");
  await expect(archive).toHaveCSS("background-image", /linear-gradient/);
  await archive.focus();
  await expect(archive).toBeFocused();
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(archive).toHaveCSS("background-image", /linear-gradient/);
  await archive.click();
  await expect(page).toHaveURL(/\/casebook$/);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  const drawerArchive = page.getByRole("dialog", { name: "Mobile navigation" }).getByRole("link", { name: "Browse historical prototype cases" });
  await expect(drawerArchive).toBeVisible();
  await expect(drawerArchive).toHaveAttribute("href", "/casebook");
});
