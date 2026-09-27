import { chromium } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const base = process.env.BASE_URL || 'http://127.0.0.1:3100';
const out = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../test-results/polish-axe.json');
const routes = ['/', '/forecast', '/casebook', '/extremes', '/ensemble', '/regimes', '/districts', '/verification', '/observations', '/quality', '/methodology', '/audit'];
const results = [];
const browser = await chromium.launch({ channel: 'chrome', headless: true });

try {
  for (const theme of ['dark', 'light']) {
    for (const width of [1440, 390]) {
      const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, reducedMotion: 'reduce' });
      if (theme === 'light') await context.addInitScript(() => localStorage.setItem('varshasetu-theme', 'light'));
      const page = await context.newPage();
      for (const route of routes) {
        try {
          await page.goto(`${base}${route}${route === '/' ? '' : '?experiment=operational&year=2025'}`, { waitUntil: 'domcontentloaded', timeout: 45_000 });
          await page.locator('main h1').first().waitFor({ timeout: 30_000 });
          const scan = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
          const violations = scan.violations.filter((item) => ['serious', 'critical'].includes(item.impact)).map((item) => ({
            id: item.id, impact: item.impact, help: item.help,
            nodes: item.nodes.map((node) => ({ target: node.target, summary: node.failureSummary })).slice(0, 8),
          }));
          results.push({ theme, width, route, violations });
        } catch (error) {
          results.push({ theme, width, route, error: String(error) });
        }
      }
      await context.close();
      console.log(`Scanned ${theme} ${width}px`);
    }
  }
} finally {
  await browser.close();
}

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, JSON.stringify(results, null, 2));
const failures = results.filter((item) => item.error || item.violations?.length);
console.log(JSON.stringify({ scans: results.length, failureCount: failures.length, failures: failures.slice(0, 10) }, null, 2));
if (failures.length) process.exitCode = 1;
