import { test, expect } from './fixtures';

test('legacy /perception page still loads without crashing', async ({ authed }) => {
  const errors: string[] = [];
  authed.on('pageerror', (err) => errors.push(err.message));

  await authed.goto('/perception');
  await expect(authed.locator('#root')).toBeVisible({ timeout: 10_000 });
  // Give the SPA time to render / mount data-fetch hooks
  await authed.waitForTimeout(2_000);
  expect(errors).toEqual([]);
});
