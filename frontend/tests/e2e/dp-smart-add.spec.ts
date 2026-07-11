import { test, expect } from './fixtures';

test.describe('smart-add data source', () => {
  test('智能添加 button opens modal with warning banner', async ({ authed }) => {
    await authed.goto('/data-platform/sources');
    await authed.getByRole('button', { name: /智能添加/ }).click();

    await expect(authed.getByText(/智能添加数据源/)).toBeVisible();
    await expect(authed.getByText(/密码字段将自动留空/)).toBeVisible();
  });

  test('parse call routes through /parse-config and reaches drawer or surfaces LLM error', async ({ authed }) => {
    await authed.goto('/data-platform/sources');
    await authed.getByRole('button', { name: /智能添加/ }).click();

    const textarea = authed.getByTestId('smart-add-textarea');
    await textarea.fill('MYSQL_HOST=127.0.0.1\nMYSQL_PORT=3306\nMYSQL_USER=test\nMYSQL_DB=demo');

    // Wait for the /parse-config request to complete. The test env has no LLM
    // credentials, so a 502 is the expected happy-path here (proves T31's
    // endpoint is wired and reachable). If LLM is available, the drawer
    // opens with "AI 已预填部分字段".
    const parsePromise = authed.waitForResponse(
      (r) => r.url().includes('/data-platform/sources/parse-config') && r.request().method() === 'POST',
      { timeout: 20_000 },
    );

    await authed.locator('.ant-modal-footer button').filter({ hasText: /解\s*析/ }).click();

    const resp = await parsePromise;
    const status = resp.status();
    if (status === 200) {
      await expect(authed.getByText(/AI 已预填部分字段/)).toBeVisible({ timeout: 15_000 });
    } else {
      expect([422, 502]).toContain(status);
    }
  });
});
