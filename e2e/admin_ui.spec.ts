import { test, expect } from '@playwright/test';

test.describe('Skelion Admin Dashboard — E2E Tests', () => {
  test('Admin login flow, KPI dashboard, and write action with step-up', async ({ page }) => {
    // 1. Visit root or admin dashboard page
    await page.goto('/dashboard');

    // 2. If unauthenticated, verify login prompt / redirect to GitHub auth
    const loginHeading = page.locator('text=Skelion Admin Panel');
    if (await loginHeading.isVisible()) {
      const loginBtn = page.locator('button:has-text("Login with GitHub")');
      await expect(loginBtn).toBeVisible();
    }

    // 3. Mock or bypass session/cookies for test if needed, or verify UI elements
    // For test robustness, let's inject a mock session cookie or mock API responses if unauthenticated
    await page.context().addCookies([
      {
        name: 'admin_session',
        value: 'mock_signed_session_token_for_e2e_test',
        domain: '127.0.0.1',
        path: '/',
      }
    ]);

    // Also mock /dashboard and /audit API responses if backend requires valid DB session
    await page.route('**/dashboard', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          kpis: { mrr: 15400, active_orgs: 42, failed_payments: 1 },
          github_user_id: 123456
        })
      });
    });

    await page.route('**/audit', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          audit: [
            { ts: '2026-11-10T12:00:00Z', actor_github_id: 123456, action: 'grant_credit', target_type: 'admin_user', target_id: 'org_1', reason: 'Test audit' }
          ]
        })
      });
    });

    // 4. Reload page with mock session
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Verify dashboard KPIs are visible
    await expect(page.locator('text=Monthly Recurring Revenue')).toBeVisible();
    await expect(page.locator('text=15,400')).toBeVisible();

    // 5. Navigate to Audit Log tab
    await page.click('text=Audit Log Viewer');
    await expect(page.locator('text=Test audit')).toBeVisible();

    // 6. Navigate to Write Actions tab
    await page.click('text=Write Actions');
    await expect(page.locator('text=Administrative Write Actions')).toBeVisible();

    // 7. Test write action and 403 step-up error handling modal trigger
    // Mock 403 step-up response first
    await page.route('**/credits/grant', async route => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Step-up authentication required' })
      });
    });

    await page.click('button:has-text("Grant Credits")');
    const stepUpModal = page.locator('text=Step-up Authentication Required');
    await expect(stepUpModal).toBeVisible();

    // Verify step-up verification interaction
    await page.route('**/factor/verify', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'verified', step_up_until: '2026-11-10T13:00:00Z', token: 'mock_step_up_token' })
      });
    });

    await page.route('**/credits/grant', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', audit_id: 'audit_uuid_12345' })
      });
    });

    await page.fill('input[placeholder="Enter 6-digit TOTP code"]', '123456');
    await page.click('button:has-text("Verify & Authorize")');

    // Screenshot for verification record
    await page.screenshot({ path: 'e2e/playwright-report/admin_dashboard_screenshot.png', fullPage: true });
  });
});
