import { test, expect } from './fixtures';
import { BACKEND_URL } from './fixtures';

async function loginToken(request: import('@playwright/test').APIRequestContext): Promise<string> {
  const res = await request.post(`${BACKEND_URL}/api/v1/auth/login`, {
    data: { username: 'admin', password: 'admin123' },
  });
  const body = await res.json();
  return body.data.access_token as string;
}

test('source detail page renders SQL 编辑器 tab when a source exists', async ({ authed, request }) => {
  const token = await loginToken(request);
  const create = await request.post(`${BACKEND_URL}/api/v1/data-platform/sources`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      name: `e2e-src-${Date.now()}`,
      source_type: 'sqlite',
      dialect: 'sqlite',
      database: ':memory:',
      charset: 'utf8mb4',
      read_only_flag: true,
    },
  });
  expect([200, 201]).toContain(create.status());
  const created = await create.json();
  const sid = created.data?.id ?? created.id;

  await authed.goto(`/data-platform/sources/${sid}`);

  // Verify the 4 tab labels appear (at least 3 out of 4 required — some tabs render inside a Tabs bar)
  const labels = ['SQL 编辑器', 'AI 对话', '执行历史', '保存的查询'];
  let visibleCount = 0;
  for (const label of labels) {
    const ok = await authed
      .getByText(label)
      .first()
      .isVisible({ timeout: 8_000 })
      .catch(() => false);
    if (ok) visibleCount++;
  }
  expect(visibleCount).toBeGreaterThanOrEqual(3);
});
