// Local, read-only visual QA for the evaluator site. Screenshots and results
// stay in ignored test-results/; this script does not change scientific data.
import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const base = process.env.VARSHA_VISUAL_BASE_URL ?? "http://127.0.0.1:3200";
const theme = process.env.VARSHA_VISUAL_THEME === "dark" ? "dark" : "light";
const out = join(process.cwd(), "test-results", theme === "dark" ? "visual-audit-dark" : "visual-audit");
const allRoutes = [
  "/", "/forecast", "/regimes", "/extremes", "/ensemble", "/districts",
  "/verification", "/india", "/live", "/observations", "/quality",
  "/zones", "/geoaware", "/casebook", "/audit", "/methodology",
  "/compliance",
];
const routes = process.env.VARSHA_VISUAL_ROUTES
  ? process.env.VARSHA_VISUAL_ROUTES.split(",").filter((route) => allRoutes.includes(route))
  : allRoutes;
const sizes = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
].filter((size) => !process.env.VARSHA_VISUAL_SIZE || size.name === process.env.VARSHA_VISUAL_SIZE);

await mkdir(out, { recursive: true });
const browser = await chromium.launch({ channel: "chrome", headless: true });
const report = [];
try {
  for (const size of sizes) {
    const context = await browser.newContext({
      viewport: { width: size.width, height: size.height },
      deviceScaleFactor: 1,
    });
    if (theme === "dark") {
      await context.addInitScript(() => localStorage.setItem("varshasetu-theme", "dark"));
    }
    for (const route of routes) {
      const page = await context.newPage();
      const errors = [];
      const localHttpErrors = [];
      page.on("pageerror", (error) => errors.push(error.message));
      page.on("response", (response) => {
        if (response.status() >= 400 && response.url().startsWith(base)) {
          localHttpErrors.push(`${response.status()} ${response.url().slice(base.length)}`);
        }
      });
      const slug = route === "/" ? "home" : route.slice(1);
      const record = { route, size: size.name };
      try {
        const response = await page.goto(`${base}${route}`, {
          waitUntil: "domcontentloaded", timeout: 45_000,
        });
        await page.waitForTimeout(1800);
        record.http = response?.status() ?? null;
        Object.assign(record, await page.evaluate(() => ({
          title: document.title,
          h1: [...document.querySelectorAll("h1")].map((node) => node.textContent?.trim()),
          width: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
          bodyText: document.body.innerText.slice(0, 700),
          brokenImages: [...document.images].filter((node) => node.complete && node.naturalWidth === 0).map((node) => node.src),
        })));
        record.horizontalOverflow = record.scrollWidth > record.width + 2;
        record.pageErrors = errors;
        record.localHttpErrors = localHttpErrors;
        await page.screenshot({ path: join(out, `${size.name}-${slug}.png`) });
        if (process.env.VARSHA_VISUAL_SCROLL === "1" && record.http === 200) {
          for (const [name, fraction] of [["middle", 0.5], ["bottom", 1]]) {
            await page.evaluate((position) => window.scrollTo(0, (document.documentElement.scrollHeight - window.innerHeight) * position), fraction);
            await page.waitForTimeout(350);
            await page.screenshot({ path: join(out, `${size.name}-${slug}-${name}.png`) });
          }
        }
        if (record.http === 200) {
          const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
          record.axe = axe.violations.map((item) => ({
            id: item.id, impact: item.impact, nodes: item.nodes.length,
            targets: item.nodes.slice(0, 3).map((node) => node.target.join(" ")),
          }));
        }
      } catch (error) {
        record.error = error instanceof Error ? error.message : String(error);
      }
      report.push(record);
      process.stdout.write(`${size.name} ${route}: HTTP ${record.http ?? "?"}, overflow=${record.horizontalOverflow ?? "?"}, pageErrors=${errors.length}, axe=${record.axe?.length ?? "-"}${record.error ? `, ERROR=${record.error}` : ""}\n`);
      await page.close();
    }
    await context.close();
  }
} finally {
  await browser.close();
  await writeFile(join(out, "report.json"), JSON.stringify(report, null, 2));
}
const failures = report.filter((record) => record.route !== "/compliance" && (
  record.http !== 200 || record.error || record.horizontalOverflow ||
  record.pageErrors?.length || record.localHttpErrors?.length ||
  record.brokenImages?.length || record.axe?.length
));
if (failures.length) {
  process.stderr.write(`Visual audit failed on ${failures.map((record) => `${record.size} ${record.route}`).join(", ")}\n`);
  process.exitCode = 1;
}
