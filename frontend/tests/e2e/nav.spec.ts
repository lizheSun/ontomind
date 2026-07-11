import { test, expect } from './fixtures';

test('top nav renders 数据平台 + 知识库 and navigates', async ({ authed }) => {
  await authed.goto('/');
  // Wait for shell / menu items to render
  await expect(authed.getByText('数据平台').first()).toBeVisible({ timeout: 10_000 });
  await expect(authed.getByText('知识库').first()).toBeVisible();
  // Click 数据平台 → land on /data-platform/sources (index redirect)
  await authed.getByText('数据平台').first().click();
  await expect(authed).toHaveURL(/\/data-platform\/sources/, { timeout: 10_000 });
  // Click 知识库 → land on /knowledge-base/data-assets
  await authed.getByText('知识库').first().click();
  await expect(authed).toHaveURL(/\/knowledge-base\/data-assets/, { timeout: 10_000 });
});

test('unauthenticated navigation redirects to /login', async ({ page }) => {
  // No token seeded on this raw page fixture
  await page.goto('/data-platform/sources');
  await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
});
