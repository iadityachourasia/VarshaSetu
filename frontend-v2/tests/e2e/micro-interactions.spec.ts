import { expect, test, type Page } from "@playwright/test";

// Micro-interactions and map interactions. Each one is checked on the animated path (automated browsers skip decorative motion unless the page is told otherwise) and
// under `prefers-reduced-motion: reduce`, where the state change must still happen but the movement must not.

const CASE = "20190802T000000Z_day3_24h";

const withMotion = async (page: Page) => { await page.addInitScript(() => { (window as unknown as { __VARSHASETU_FORCE_MOTION__: boolean }).__VARSHASETU_FORCE_MOTION__ = true; }); };
const reduced = async (page: Page) => { await page.emulateMedia({ reducedMotion: "reduce" }); };

test.describe("sliding segmented control", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`the highlight follows the selected button (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/extremes?case=${CASE}`);
      const group = page.getByRole("group", { name: "Event threshold" });
      await expect(group).toHaveClass(/segmented-ready/);
      const thumb = group.locator(".segmented-thumb");
      const overlap = async (name: RegExp) => {
        const button = await group.getByRole("button", { name }).boundingBox();
        const box = await thumb.boundingBox();
        return Math.abs((box?.x ?? -999) - (button?.x ?? 999)) < 2 && Math.abs((box?.width ?? 0) - (button?.width ?? 1)) < 2;
      };
      await expect.poll(() => overlap(/^Heavy/)).toBe(true);
      await group.getByRole("button", { name: /^Very Heavy/ }).click();
      await expect(group.getByRole("button", { name: /^Very Heavy/ })).toHaveAttribute("aria-pressed", "true");
      await expect(group.getByRole("button", { name: /^Heavy ·/ })).toHaveAttribute("aria-pressed", "false");
      await expect.poll(() => overlap(/^Very Heavy/), { timeout: 3000 }).toBe(true);
      if (mode === "animated") await expect(group).toHaveClass(/segmented-animated/);
      else await expect(group).not.toHaveClass(/segmented-animated/);
    });
  }
});

test.describe("copy-hash chip and toast", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`a digest chip copies the full SHA-256 and confirms it (${mode})`, async ({ page, context }) => {
      await context.grantPermissions(["clipboard-read", "clipboard-write"]);
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto("/verification");
      const chip = page.locator(".hash-chip").first();
      await chip.scrollIntoViewIfNeeded();
      const full = await chip.getAttribute("data-hash");
      expect(full).toMatch(/^[0-9a-f]{64}$/);
      await expect(chip).toHaveText(`${full!.slice(0, 12)}…`);
      await chip.click();
      const toast = page.getByTestId("toast-region").getByText("Full SHA-256 copied");
      await expect(toast).toBeVisible();
      expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(full);
      const animation = await toast.evaluate((node) => getComputedStyle(node).animationName);
      expect(animation).toBe(mode === "animated" ? "toast-in" : "none");
      await expect(toast).toBeHidden({ timeout: 6000 });
    });
  }

  test("a report link still downloads, and says that it started", async ({ page }) => {
    await page.goto("/verification");
    const link = page.getByRole("link", { name: "Markdown", exact: true }).first();
    await link.scrollIntoViewIfNeeded();
    const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
    expect(download.suggestedFilename()).toMatch(/\.md$/);
    await expect(page.getByTestId("toast-region").getByText("Download started")).toBeVisible();
  });
});

test.describe("count-up on the headline numbers", () => {
  const record = async (page: Page) => {
    await page.addInitScript(() => {
      const seen: string[] = [];
      (window as unknown as { __counted: string[] }).__counted = seen;
      new MutationObserver((records) => {
        for (const entry of records) {
          const node = entry.target instanceof Element ? entry.target : entry.target.parentElement;
          const holder = node?.closest("[data-countup]");
          const panel = holder?.parentElement?.closest(".overview-benchmark-improvement");
          // Only the first headline number on the page is followed.
          if (panel && panel === document.querySelector(".overview-benchmark-improvement")) seen.push(holder?.textContent ?? "");
        }
      }).observe(document, { subtree: true, childList: true, characterData: true });
    });
  };
  const finalText = async (page: Page) => page.locator(".overview-benchmark-improvement [data-countup]").first().textContent();

  test("counts up and lands on exactly the written value, never above it", async ({ page }) => {
    await withMotion(page);
    await record(page);
    await page.goto("/");
    const holder = page.locator(".overview-benchmark-improvement [data-countup]").first();
    await expect(holder).toBeVisible();
    await page.waitForTimeout(1600);
    const final = await finalText(page);
    expect(final).toMatch(/^\d+\.\d{2}$/);
    const seen = await page.evaluate(() => (window as unknown as { __counted: string[] }).__counted);
    expect(seen.length).toBeGreaterThan(3);
    expect(seen[seen.length - 1]).toBe(final);
    for (const text of seen) expect(Number(text)).toBeLessThanOrEqual(Number(final) + 1e-9);
  });

  test("under reduced motion the number is simply there", async ({ page }) => {
    await reduced(page);
    await record(page);
    await page.goto("/");
    await expect(page.locator(".overview-benchmark-improvement [data-countup]").first()).toBeVisible();
    await page.waitForTimeout(1200);
    // Hydration may touch the text node, but no intermediate value is ever written.
    const seen = await page.evaluate(() => (window as unknown as { __counted: string[] }).__counted);
    const final = await finalText(page);
    expect(final).toMatch(/^\d+\.\d{2}$/);
    for (const text of seen) expect(text).toBe(final);
  });
});

test.describe("scroll-spy in the page contents", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`the link of the section being read is marked (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto("/verification");
      const toc = page.getByTestId("page-toc");
      await expect(toc).toBeVisible();
      const links = toc.locator("a");
      expect(await links.count()).toBeGreaterThanOrEqual(5);
      for (const index of [2, 4]) {
        const href = await links.nth(index).getAttribute("href");
        await page.evaluate((id) => { const top = document.getElementById(id)!.getBoundingClientRect().top + window.scrollY; window.scrollTo(0, top - 100); }, href!.slice(1));
        await expect(links.nth(index)).toHaveAttribute("aria-current", "location");
        await expect(toc.locator("a[aria-current='location']")).toHaveCount(1);
      }
    });
  }
});

test.describe("forest plot", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`intervals draw in, and each row has its own readable tooltip (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto("/verification");
      const forest = page.getByTestId("regime-forest").first();
      await forest.scrollIntoViewIfNeeded();
      const interval = forest.locator(".forest-interval").first();
      expect(await interval.evaluate((node) => getComputedStyle(node).animationName)).toBe(mode === "animated" ? "forest-draw" : "none");
      const rowTitles = await forest.locator("svg").first().locator("g.forest-row > title").allTextContents();
      expect(rowTitles.length).toBeGreaterThanOrEqual(3);
      for (const text of rowTitles) expect(text).toMatch(/: (not reported|[+-]?\d+\.\d{3} \(interval -?\d+\.\d{3} to -?\d+\.\d{3}\) (excludes|includes) zero)$/);
    });
  }
});

test.describe("map interactions on the three Forecast maps", () => {
  const maps = (page: Page) => page.locator(".map-canvas[data-ready='true']");

  for (const mode of ["animated", "reduced"] as const) {
    test(`hovering a legend class emphasises it on every map, and leaving restores them (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/forecast?case=${CASE}`);
      await expect(maps(page)).toHaveCount(3);
      const bins = page.locator(".legend-bin");
      await bins.nth(2).hover();
      for (let index = 0; index < 3; index++) await expect(maps(page).nth(index)).toHaveAttribute("data-emphasis", "5:20");
      await expect(page.locator(".legend-bins")).toHaveClass(/legend-bins-active/);
      await page.mouse.move(5, 5);
      for (let index = 0; index < 3; index++) await expect(maps(page).nth(index)).toHaveAttribute("data-emphasis", "");
      await bins.nth(5).focus();
      for (let index = 0; index < 3; index++) await expect(maps(page).nth(index)).toHaveAttribute("data-emphasis", "64.5:115.6");
      await bins.nth(5).blur();
      for (let index = 0; index < 3; index++) await expect(maps(page).nth(index)).toHaveAttribute("data-emphasis", "");
    });

    test(`one pointer is shared by the three maps (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/forecast?case=${CASE}`);
      await expect(maps(page)).toHaveCount(3);
      const raw = await maps(page).nth(0).boundingBox();
      await page.mouse.move(raw!.x + raw!.width / 2, raw!.y + raw!.height / 2);
      await page.mouse.move(raw!.x + raw!.width / 2 + 6, raw!.y + raw!.height / 2 + 4);
      await expect(maps(page).nth(1)).toHaveAttribute("data-linked-hover", /^\d+,\d+$/);
      const first = await maps(page).nth(1).getAttribute("data-linked-hover");
      await expect(maps(page).nth(2)).toHaveAttribute("data-linked-hover", first!);
      await page.mouse.move(raw!.x + raw!.width / 2 + 90, raw!.y + raw!.height / 2 + 60);
      await expect.poll(() => maps(page).nth(2).getAttribute("data-linked-hover")).not.toBe(first);
      await page.mouse.move(2, 2);
      await expect(maps(page).nth(1)).toHaveAttribute("data-linked-hover", "");
    });

    test(`choosing a cell rings it only when motion is allowed, and switching the corrected model crossfades (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/forecast?case=${CASE}`);
      await expect(maps(page)).toHaveCount(3);
      const corrected = maps(page).nth(1);
      const box = await corrected.boundingBox();
      await page.mouse.click(box!.x + box!.width * 0.35, box!.y + box!.height * 0.4);
      await page.mouse.click(box!.x + box!.width * 0.6, box!.y + box!.height * 0.55);
      // A new case replaces the triptych with its loading state (the maps are rebuilt), so the picture swap that crossfades is the corrected-model switch, on the same maps.
      await page.getByRole("group", { name: "Corrected model" }).getByRole("button", { name: /B1/ }).click();
      await expect(page.getByTestId("heavy-rain-notice")).toContainText("RMSE B1");
      await page.waitForTimeout(700);
      const pulses = Number((await corrected.getAttribute("data-pulses")) ?? "0");
      const crossfades = Number((await corrected.getAttribute("data-crossfades")) ?? "0");
      if (mode === "animated") { expect(pulses).toBeGreaterThanOrEqual(1); expect(crossfades).toBeGreaterThanOrEqual(1); }
      else { expect(pulses).toBe(0); expect(crossfades).toBe(0); }
      // Whatever the motion setting, the scientific layer is installed and the selected cell outline is on the map.
      await expect(corrected).toHaveAttribute("data-ready", "true");
    });
  }
});

test.describe("district table and map are linked", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`pointing at a row outlines its polygon (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/districts?case=${CASE}`);
      const map = page.locator(".district-map[data-ready='true']");
      await expect(map).toBeVisible();
      const row = page.locator(".district-table tbody tr").nth(3);
      await row.scrollIntoViewIfNeeded();
      await row.hover();
      await expect(row).toHaveClass(/linked-row/);
      await expect(map).toHaveAttribute("data-hovered", /.+/);
      await page.mouse.move(2, 2);
      await expect(row).not.toHaveClass(/linked-row/);
      await expect(map).toHaveAttribute("data-hovered", "");
    });
  }
});

test.describe("loading state to content", () => {
  for (const mode of ["animated", "reduced"] as const) {
    test(`new content fades in instead of snapping, only when motion is allowed (${mode})`, async ({ page }) => {
      await (mode === "animated" ? withMotion(page) : reduced(page));
      await page.goto(`/forecast?case=${CASE}`);
      await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
      await page.evaluate(() => {
        const state = window as unknown as { __fades: number };
        state.__fades = 0;
        document.addEventListener("animationstart", (event) => { if (event.animationName === "content-in") state.__fades += 1; }, true);
      });
      await page.getByRole("button", { name: "Previous case" }).click();
      await expect(page.locator(".map-canvas[data-ready='true']")).toHaveCount(3);
      const fades = await page.evaluate(() => (window as unknown as { __fades: number }).__fades);
      if (mode === "animated") expect(fades).toBeGreaterThanOrEqual(1);
      else expect(fades).toBe(0);
    });
  }
});
