import { chromium } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const base = process.env.BASE_URL || 'http://127.0.0.1:3100';
const out = process.env.CAPTURE_OUT ? path.resolve(process.env.CAPTURE_OUT) : path.resolve(__dirname, '../../test-results/polish-sweep');
const viewFilter = process.env.CAPTURE_WIDTHS?.split(',');
const views = [[1440, 900], [1366, 768], [820, 1080], [390, 844]].filter(([width]) => !viewFilter || viewFilter.includes(String(width)));
const routeFilter = process.env.CAPTURE_ROUTES?.split(',');
const routes = [
  ['overview', '/'],
  ...['forecast', 'casebook', 'extremes', 'ensemble', 'regimes', 'districts', 'verification', 'observations', 'quality', 'methodology', 'audit']
    .map((name) => [name, `/${name}${['quality', 'methodology', 'audit', 'observations'].includes(name) ? '' : '?experiment=operational&year=2025'}`]),
  ['forecast-2023', '/forecast?experiment=operational&year=2023'],
  ['forecast-2024', '/forecast?experiment=operational&year=2024'],
  ['forecast-2019', '/forecast?experiment=reforecast&year=2019'],
].filter(([name]) => !routeFilter || routeFilter.includes(name));

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const results = [];
  for (const theme of ['dark', 'light']) {
    for (const [width, height] of views) {
      const context = await browser.newContext({ viewport: { width, height }, reducedMotion: 'reduce' });
      if (theme === 'light') await context.addInitScript(() => localStorage.setItem('varshasetu-theme', 'light'));
      const page = await context.newPage();
      for (const [name, route] of routes) {
        const errors = [];
        page.on('pageerror', (error) => errors.push(error.message));
        try {
          const response = await page.goto(base + route, { waitUntil: 'domcontentloaded', timeout: 30000 });
          await page.locator('main h1').first().waitFor({ timeout: 20000 });
          if (name.startsWith('forecast')) await page.locator('.map-canvas[data-ready="true"]').first().waitFor({ timeout: 20000 }).catch(() => {});
          if (name === 'verification') await page.locator('.chart-figure svg.recharts-surface').first().waitFor({ timeout: 10000 }).catch(() => {});
          await page.screenshot({ path: path.join(out, `${theme}-${width}-${name}.png`) });
          const metrics = await page.evaluate(() => ({
            overflow: document.documentElement.scrollWidth - innerWidth,
            heading: document.querySelector('main h1')?.textContent?.trim(),
            maps: document.querySelectorAll('.map-canvas[data-ready="true"]').length,
            charts: document.querySelectorAll('.chart-figure svg.recharts-surface').length,
            appliedTheme: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
            cssValid: (() => {
              const localSheets = [...document.styleSheets].filter((sheet) => sheet.href?.startsWith(location.origin));
              const readable = localSheets.length > 0 && localSheets.every((sheet) => {
                try { return sheet.cssRules.length > 0; } catch { return false; }
              });
              const root = getComputedStyle(document.documentElement);
              const header = document.querySelector('.global-header');
              return readable && Boolean(root.getPropertyValue('--surface-raised').trim())
                && Boolean(header) && getComputedStyle(header).position === 'sticky';
            })(),
          }));
          results.push({ theme, width, route: name, status: response?.status(), ...metrics, errors });
        } catch (error) { results.push({ theme, width, route: name, error: String(error), errors }); }
        page.removeAllListeners('pageerror');
      }
      await context.close();
      console.log(`Captured ${theme} ${width}px`);
    }
  }
  await browser.close();
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(results, null, 2));
  const failures = results.filter((item) => item.error || item.status !== 200 || item.overflow > 1 || item.errors.length || item.theme !== item.appliedTheme || (process.env.CSS_GATE !== '0' && !item.cssValid));
  console.log(JSON.stringify({ captures: results.length, failureCount: failures.length, failures: failures.slice(0, 10) }, null, 2));
  if (failures.length) process.exitCode = 1;
})().catch((error) => { console.error(error); process.exitCode = 1; });

