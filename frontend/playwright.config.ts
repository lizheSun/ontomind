import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5179';
const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL ?? 'http://127.0.0.1:8004';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  expect: { timeout: 8_000 },
  fullyParallel: false,
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    extraHTTPHeaders: { 'X-Backend': BACKEND_URL },
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } } },
  ],
  // T27: dedicated E2E backend+frontend are booted externally by the task
  // runner on ports 8004/5179 to keep tests isolated from the dev servers.
  // Manual boot: FERNET_KEY=... uvicorn ...port 8004; vite --port 5179.
  // webServer: [
  //   { command: 'npm run dev', url: BASE_URL, reuseExistingServer: true, timeout: 60_000 },
  //   { command: 'cd ../backend && venv/bin/uvicorn app.main:app --port 8000', url: `${BACKEND_URL}/health`, reuseExistingServer: true, timeout: 60_000 },
  // ],
});
