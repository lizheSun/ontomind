import { test as base, expect, type Page } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? 'http://127.0.0.1:8005';

const OUTPUT_DIR = path.resolve(process.cwd(), '../.blueprint/qa/T28/screenshots');
const CONSOLE_LOG = path.resolve(process.cwd(), '../.blueprint/qa/T28/console.log');

const PAGES = [
  { slug: 'dp-sources', path: '/data-platform/sources' },
  { slug: 'kb-data-assets', path: '/knowledge-base/data-assets' },
  { slug: 'kb-search', path: '/knowledge-base/search?q=test' },
  { slug: 'perception-legacy', path: '/perception' },
  { slug: 'dashboard', path: '/' },
] as const;

const VIEWPORTS = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1280', width: 1280, height: 800 },
] as const;

async function mintJwt(request: any) {
  const res = await request.post(`${BACKEND}/api/v1/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  const body = await res.json();
  return body.data?.access_token ?? body.access_token;
}

const test = base.extend<{ authed: Page }>({
  authed: async ({ page, request }, use) => {
    const token = await mintJwt(request);
    await page.addInitScript((t) => {
      window.localStorage.setItem('access_token', t);
    }, token);
    await use(page);
  },
});

test.beforeAll(async () => {
  await fs.mkdir(OUTPUT_DIR, { recursive: true });
  await fs.writeFile(CONSOLE_LOG, `# T28 console.log — captured ${new Date().toISOString()}\n\n`);
});

for (const p of PAGES) {
  for (const v of VIEWPORTS) {
    test(`${p.slug} @ ${v.name}`, async ({ authed }) => {
      const consoleErrs: string[] = [];
      const pageErrs: string[] = [];
      authed.on('console', (m) => {
        if (m.type() === 'error') consoleErrs.push(m.text());
      });
      authed.on('pageerror', (e) => pageErrs.push(e.message));

      await authed.setViewportSize({ width: v.width, height: v.height });
      await authed.goto(p.path);

      // Wait for #root to have content (SPA hydrated)
      await authed
        .waitForFunction(
          () => (document.getElementById('root')?.children.length ?? 0) > 0,
          undefined,
          { timeout: 10_000 },
        )
        .catch(() => {
          /* proceed even if hydration slow */
        });

      await authed.waitForTimeout(1_500); // let animations/data-fetches settle

      const shot = path.join(OUTPUT_DIR, `${p.slug}-${v.name}.png`);
      await authed.screenshot({ path: shot, fullPage: true });

      const summary =
        `## ${p.slug} @ ${v.name}\n` +
        `- console.error: ${consoleErrs.length}\n` +
        `- pageerror: ${pageErrs.length}\n` +
        (consoleErrs.length
          ? '### console.error samples\n' +
            consoleErrs.slice(0, 5).map((e) => `- ${e}`).join('\n') +
            '\n'
          : '') +
        (pageErrs.length
          ? '### pageerror samples\n' +
            pageErrs.slice(0, 5).map((e) => `- ${e}`).join('\n') +
            '\n'
          : '') +
        '\n';
      await fs.appendFile(CONSOLE_LOG, summary);

      if (consoleErrs.length + pageErrs.length > 0) {
        console.log(
          `[${p.slug} @ ${v.name}] console errs: ${consoleErrs.length}, page errs: ${pageErrs.length}`,
        );
        console.log(consoleErrs.slice(0, 3).join('\n'));
        console.log(pageErrs.slice(0, 3).join('\n'));
      }

      // For new pages (not /perception, /dashboard = legacy), assert clean
      if (!['perception-legacy', 'dashboard'].includes(p.slug)) {
        expect(pageErrs, `${p.slug} produced page errors: ${pageErrs.join('; ')}`).toEqual([]);
      }
    });
  }
}
