import { test as base, type Page, type APIRequestContext } from '@playwright/test';

const BACKEND = process.env.PLAYWRIGHT_BACKEND_URL ?? 'http://127.0.0.1:8004';

export async function mintJwtViaApi(request: APIRequestContext): Promise<string> {
  const res = await request.post(`${BACKEND}/api/v1/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  if (!res.ok()) throw new Error(`Login failed ${res.status()} ${await res.text()}`);
  const body = await res.json();
  const token = body.data?.access_token ?? body.access_token;
  if (!token) throw new Error(`No token in response: ${JSON.stringify(body)}`);
  return token;
}

export const test = base.extend<{ authed: Page }>({
  authed: async ({ page, request }, use) => {
    const token = await mintJwtViaApi(request);
    // Seed localStorage before page loads
    await page.addInitScript((t) => {
      window.localStorage.setItem('access_token', t);
    }, token);
    await use(page);
  },
});

export { expect } from '@playwright/test';

export const BACKEND_URL = BACKEND;
