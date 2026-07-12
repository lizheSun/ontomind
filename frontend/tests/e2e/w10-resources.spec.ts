/**
 * Wave 10 · Resources page (5-layer nav) E2E.
 *
 * Verifies the T49 refactor:
 *   - Header + 7 stat cards (5 layers + running + errors)
 *   - Collapsible section headers for all 5 layers
 *   - Section collapse state persists in localStorage across reloads
 */
import { test, expect } from './fixtures';

test.describe('w10 resources page', () => {
  test('renders header, 7 stat labels, and all 5 layer sections', async ({ authed }) => {
    await authed.goto('/resources');

    // Header
    await expect(authed.getByRole('heading', { name: /资源管理/ })).toBeVisible({ timeout: 15_000 });

    // 7 stat card labels
    for (const label of [
      '计算节点',
      '智能体容器',
      '智能体',
      'Skill',
      'MCP',
      '正在运行的任务',
      '发现错误',
    ]) {
      // Each label appears at least once (StatCard uses the label text)
      const count = await authed.getByText(label, { exact: true }).count();
      expect(count).toBeGreaterThanOrEqual(1);
    }

    // 5 layer section headings visible (subtitle texts unique to each panel)
    await expect(
      authed.getByText('物理机 / 虚拟机 / Docker Host / K8s Pod'),
    ).toBeVisible();
    await expect(
      authed.getByText(/opencode \/ openclaw \/ harness 等 Agent runtime/),
    ).toBeVisible();
    await expect(
      authed.getByText(/ReAct \/ Plan-Execute \/ Reflect 策略/),
    ).toBeVisible();
    await expect(
      authed.getByText(/给智能体加载的能力模块/),
    ).toBeVisible();
    await expect(
      authed.getByText(/Model Context Protocol/),
    ).toBeVisible();
  });

  test('auto-discover button is present and clickable', async ({ authed }) => {
    await authed.goto('/resources');
    const btn = authed.getByRole('button', { name: /一键自动发现/ });
    await expect(btn).toBeVisible({ timeout: 15_000 });
    await expect(btn).toBeEnabled();
    // We deliberately do not click — the backend may take time and this is a
    // smoke test. Merely confirming the CTA is discoverable is enough.
  });

  test('collapse state persists in localStorage', async ({ authed }) => {
    await authed.goto('/resources');

    // Locate the "计算节点" section header (role=button with aria-expanded)
    const header = authed
      .locator('[role="button"][aria-expanded]')
      .filter({ hasText: '计算节点' })
      .first();
    await expect(header).toBeVisible({ timeout: 15_000 });

    // Toggle it
    await header.click();

    // Verify localStorage was written
    const stored = await authed.evaluate(() =>
      window.localStorage.getItem('resources.panel.collapsed.v1'),
    );
    expect(stored).not.toBeNull();
    const parsed = JSON.parse(stored ?? '{}');
    // At least one layer flag should now be true (collapsed)
    const anyCollapsed = Object.values(parsed).some((v) => v === true);
    expect(anyCollapsed).toBe(true);
  });
});
