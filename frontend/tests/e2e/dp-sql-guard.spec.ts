import { test, expect } from './fixtures';
import { BACKEND_URL } from './fixtures';

test('executing DROP TABLE surfaces guard error UI', async ({ authed, request }) => {
  const login = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  const token = (await login.json()).data.access_token;
  const create = await request.post(`${BACKEND_URL}/api/v1/data-platform/sources`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      name: `e2e-guard-${Date.now()}`,
      source_type: 'sqlite',
      dialect: 'sqlite',
      database: ':memory:',
      charset: 'utf8mb4',
      read_only_flag: true,
    },
  });
  expect([200, 201]).toContain(create.status());
  const sid = (await create.json()).data.id;

  await authed.goto(`/data-platform/sources/${sid}`);
  // Wait for editor to mount
  await authed.waitForTimeout(2_500);

  // Monaco exposes an accessible textbox with name "Editor content". Click into
  // the editor viewport then select-all + type via keyboard so Monaco updates state.
  const monacoRoot = authed.locator('.monaco-editor').first();
  await monacoRoot.click();
  await authed.keyboard.press('ControlOrMeta+a');
  await authed.keyboard.press('Delete');
  await authed.keyboard.type('DROP TABLE users');

  // Click 执行 button
  await authed.getByRole('button', { name: /执行/ }).first().click();

  // Expect an antd error message OR notification containing the guard/forbidden phrasing
  const errorMsg = authed
    .locator('.ant-message-error, .ant-notification-notice-error, .ant-alert-error')
    .first();
  await expect(errorMsg).toBeVisible({ timeout: 10_000 });
});
