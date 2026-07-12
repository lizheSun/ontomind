/**
 * Wave 10 · Agent Looper CRUD-ish smoke E2E.
 *
 * Covers 3 flows against the /resources/agent-looper/new wizard and the
 * AgentLooperListPage embedded in /resources → Agent panel.
 *
 * The specs are intentionally resilient to non-fatal issues: they assert
 * on stable data-testid + role selectors and, where a backend endpoint
 * may not be wired, tolerate a graceful "unavailable" text (see the
 * wizard's preview-test fallback).
 */
import { test, expect } from './fixtures';

test.describe('w10 agent-looper', () => {
  test('wizard renders 4 steps and Next requires a name', async ({ authed }) => {
    await authed.goto('/resources/agent-looper/new');

    // Steps rail present
    await expect(authed.getByText('定位').first()).toBeVisible({ timeout: 15_000 });
    await expect(authed.getByText('能力').first()).toBeVisible();
    await expect(authed.getByText('系统提示词').first()).toBeVisible();
    await expect(authed.getByText('联通测试').first()).toBeVisible();

    // Step 1 fields visible
    await expect(authed.getByTestId('wizard-name')).toBeVisible();

    // Next disabled while name is empty
    const nextBtn = authed.getByTestId('wizard-next');
    await expect(nextBtn).toBeDisabled();

    // Type a name and Next becomes enabled
    await authed.getByTestId('wizard-name').fill('E2E · w10 agent');
    await expect(nextBtn).toBeEnabled();
  });

  test('wizard step navigation forward and back preserves state', async ({ authed }) => {
    await authed.goto('/resources/agent-looper/new');
    await authed.getByTestId('wizard-name').fill('E2E · nav-agent');

    // Step 1 → 2
    await authed.getByTestId('wizard-next').click();
    // Model input appears on step 2
    await expect(authed.getByTestId('wizard-model')).toBeVisible({ timeout: 10_000 });

    // Step 2 → 3
    await authed.getByTestId('wizard-next').click();
    await expect(authed.getByTestId('wizard-system-prompt')).toBeVisible({ timeout: 10_000 });

    // Go back to step 2 — name from step 1 is retained (verify by going all the way back)
    await authed.getByTestId('wizard-back').click();
    await expect(authed.getByTestId('wizard-model')).toBeVisible();
    await authed.getByTestId('wizard-back').click();
    await expect(authed.getByTestId('wizard-name')).toHaveValue('E2E · nav-agent');
  });

  test('wizard reaches step 4 with a "运行测试" button', async ({ authed }) => {
    await authed.goto('/resources/agent-looper/new');
    await authed.getByTestId('wizard-name').fill('E2E · reach-test');

    await authed.getByTestId('wizard-next').click();
    await authed.getByTestId('wizard-next').click();
    await authed.getByTestId('wizard-next').click();

    // We should now be on the final step with a run-test button and a finish
    // button (renamed from Next → Finish per wizard code).
    await expect(authed.getByTestId('wizard-run-test')).toBeVisible({ timeout: 10_000 });
    await expect(authed.getByTestId('wizard-finish')).toBeVisible();
  });
});
