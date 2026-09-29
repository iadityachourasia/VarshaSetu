import { expect, test } from "@playwright/test";

test("generated favicon metadata appears once across routes", async ({ page }) => {
  for (const route of ["/", "/forecast?experiment=reforecast&year=2019", "/verification"]) {
    await page.goto(route);
    await expect(page.locator('head link[rel="icon"][href="/favicon-96x96.png"][sizes="96x96"][type="image/png"]')).toHaveCount(1);
    await expect(page.locator('head link[rel="icon"][href="/favicon.svg"][type="image/svg+xml"]')).toHaveCount(1);
    await expect(page.locator('head link[rel="shortcut icon"][href="/favicon.ico"]')).toHaveCount(1);
    await expect(page.locator('head link[rel="apple-touch-icon"][href="/apple-touch-icon.png"][sizes="180x180"]')).toHaveCount(1);
    await expect(page.locator('head meta[name="apple-mobile-web-app-title"][content="VarshaSetu"]')).toHaveCount(1);
    await expect(page.locator('head link[rel="manifest"][href="/site.webmanifest"]')).toHaveCount(1);
    await expect(page.locator('head link[rel="icon"]')).toHaveCount(2);
  }
});

test("all generated favicon assets are publicly served", async ({ request }) => {
  for (const file of [
    "favicon.svg",
    "favicon-96x96.png",
    "favicon.ico",
    "apple-touch-icon.png",
    "web-app-manifest-192x192.png",
    "web-app-manifest-512x512.png",
    "site.webmanifest",
  ]) {
    const response = await request.get(`/${file}`);
    expect(response.ok(), file).toBe(true);
    expect(Number(response.headers()["content-length"] ?? (await response.body()).length), file).toBeGreaterThan(0);
  }
  const manifest = await (await request.get("/site.webmanifest")).json();
  expect(manifest.name).toBe("VarshaSetu");
  expect(manifest.icons).toHaveLength(2);
});
