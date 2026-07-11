import { test, expect } from './fixtures';

test.describe('data-platform metadata page', () => {
  test('metadata page loads and shows sub-nav', async ({ authed }) => {
    await authed.goto('/data-platform/metadata');
    // The "元数据浏览" card only mounts after a data source is picked; the
    // stable landmark on first load is the sub-nav Radio.Group with both
    // options rendered as Radio.Button labels (visible spans).
    await expect(authed.getByRole('radio', { name: /元数据/ })).toBeAttached();
    await expect(authed.getByRole('radio', { name: /数据源/ })).toBeAttached();
    await expect(authed.getByText(/选择要浏览的数据源/)).toBeVisible();
  });

  test('sub-nav switches from metadata to sources', async ({ authed }) => {
    await authed.goto('/data-platform/metadata');
    // Radio.Button's native <input> is display:none; click the visible label
    // (Ant Design's outer span carrying the text) via the Radio label locator.
    await authed.locator('label.ant-radio-button-wrapper').filter({ hasText: /数据源/ }).click();
    await expect(authed).toHaveURL(/\/data-platform\/sources/);
  });
});
