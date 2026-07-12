/**
 * Wave 10 · UX layer E2E.
 *
 * Covers:
 *   - Cmd+K omnibar (T57): global keyboard shortcut opens a modal with an
 *     input and >=1 result row, then Esc closes it.
 *   - Zen/God dual-mode toggle (T58): clicking the floating eye button flips
 *     <html data-ui-mode="…"> and persists to localStorage['ui:mode'].
 */
import { test, expect } from './fixtures';

test.describe('w10 UX', () => {
  test('Cmd+K opens the omnibar and Esc closes it', async ({ authed }) => {
    await authed.goto('/');

    // Give the shell a beat to mount the global keydown listener
    await expect(authed.locator('#root')).toBeVisible({ timeout: 15_000 });

    // Trigger Cmd+K (macOS) — Playwright normalizes Meta on Chromium
    await authed.keyboard.press('Meta+k');

    // Omnibar input becomes visible
    const searchInput = authed.getByLabel('Cmd+K omnibar');
    await expect(searchInput).toBeVisible({ timeout: 5_000 });

    // At least one listbox result row rendered by default
    const listbox = authed.getByRole('listbox', { name: 'omnibar-results' });
    await expect(listbox).toBeVisible();
    const options = listbox.getByRole('option');
    expect(await options.count()).toBeGreaterThan(0);

    // Escape closes the modal
    await authed.keyboard.press('Escape');
    await expect(searchInput).toBeHidden({ timeout: 5_000 });
  });

  test('Zen/God toggle flips <html data-ui-mode> and persists', async ({ authed }) => {
    await authed.goto('/');

    // Read initial state (defaults to 'zen')
    const initialMode = await authed.evaluate(() =>
      document.documentElement.getAttribute('data-ui-mode'),
    );
    expect(['zen', 'god', null]).toContain(initialMode);

    // The toggle button uses aria-label starting with the configured prefix
    const toggle = authed.getByRole('button', { name: /界面模式:/ });
    await expect(toggle).toBeVisible({ timeout: 15_000 });
    await toggle.click();

    // After click, data-ui-mode should be defined & be zen/god
    const afterMode = await authed.evaluate(() =>
      document.documentElement.getAttribute('data-ui-mode'),
    );
    expect(['zen', 'god']).toContain(afterMode ?? '');
    // And it must differ from the initial mode (guarantees the click had effect)
    expect(afterMode).not.toBe(initialMode ?? 'zen');

    // localStorage is now populated with the same value
    const stored = await authed.evaluate(() =>
      window.localStorage.getItem('ui:mode'),
    );
    expect(stored).toBe(afterMode);
  });
});
