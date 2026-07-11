import { test, expect } from './fixtures';

const CASES = [
  { path: '/knowledge-base/data-assets', title: '数据资产' },
  { path: '/knowledge-base/code-repos', title: '代码库' },
  { path: '/knowledge-base/documents', title: '文档库' },
  { path: '/knowledge-base/experiences', title: '业务经验库' },
] as const;

for (const { path, title } of CASES) {
  test(`KB sub-lib "${title}" page loads and shows title`, async ({ authed }) => {
    await authed.goto(path);
    await expect(authed.getByText(title).first()).toBeVisible({ timeout: 10_000 });
  });
}
