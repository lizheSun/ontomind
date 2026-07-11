import { test, expect } from './fixtures';

test('sources list page shows header + subtitle', async ({ authed }) => {
  await authed.goto('/data-platform/sources');
  await expect(authed.getByText('数据平台 · 数据源')).toBeVisible({ timeout: 10_000 });
  await expect(authed.getByText('连接、探查、并对话你的数据资产')).toBeVisible();
  // Either the empty-state message OR the CTA button must be visible
  const hasEmpty = await authed.getByText('暂无数据源').isVisible().catch(() => false);
  const hasCreateBtn = await authed
    .getByRole('button', { name: /新建数据源/ })
    .first()
    .isVisible()
    .catch(() => false);
  expect(hasEmpty || hasCreateBtn).toBe(true);
});

test('opening the create drawer shows dialect segmented options', async ({ authed }) => {
  await authed.goto('/data-platform/sources');
  await authed.getByRole('button', { name: /新建数据源/ }).first().click();
  // Drawer visible (title uses the same 新建数据源 label)
  await expect(authed.locator('.ant-drawer').first()).toBeVisible({ timeout: 5_000 });
  await expect(authed.getByText('MySQL').first()).toBeVisible();
  await expect(authed.getByText('PostgreSQL').first()).toBeVisible();
  await expect(authed.getByText('SQLite').first()).toBeVisible();
});
