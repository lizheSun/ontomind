import { defineConfig, devices } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? 'http://localhost:5173';
const BACKEND_URL = process.env.PLAYWRIGHT_BACKEND_URL ?? 'http://localhost:8000';

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
  // Assume the dev servers are already running (they are: PID 76383 / 78449).
  // For CI/fresh boots, uncomment webServer.
  // webServer: [
  //   { command: 'npm run dev', url: BASE_URL, reuseExistingServer: true, timeout: 60_000 },
  //   { command: 'cd ../backend && venv/bin/uvicorn app.main:app --port 8000', url: `${BACKEND_URL}/health`, reuseExistingServer: true, timeout: 60_000 },
  // ],
});
