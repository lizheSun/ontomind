import { test, expect } from './fixtures';

test('KB search page shows pre-search empty state', async ({ authed }) => {
  await authed.goto('/knowledge-base/search');
  await expect(authed.getByText(/输入关键词开始搜索/).first()).toBeVisible({ timeout: 10_000 });
});

test('typing query in URL shows filter chips (全部 + 数据资产)', async ({ authed }) => {
  await authed.goto('/knowledge-base/search?q=test');
  await expect(authed.getByText('全部').first()).toBeVisible({ timeout: 10_000 });
  await expect(authed.getByText('数据资产').first()).toBeVisible();
});
