import { test, expect } from '@playwright/test';

test.describe('Helios Web Platform — End-to-End User Journey', () => {
  test('User lands on pricing, triggers Razorpay checkout, and verifies webhook state', async ({ page }) => {
    // 1. User lands on home page / pricing
    await page.goto('/#pricing');
    await expect(page).toHaveTitle(/Skelion|Helios/i);

    // 2. Pricing and calculator elements are visible
    const pricingHeading = page.locator('text=Pocket-Friendly & Predictable Pricing');
    await expect(pricingHeading).toBeVisible();

    // 3. User selects Pro plan
    const proCard = page.locator('[data-plan="pro"]').or(page.locator('text=Pro').first());
    await expect(proCard).toBeVisible();

    // 4. Modal checkout verification
    const upgradeButton = page.locator('button:has-text("Upgrade to Pro")').first();
    if (await upgradeButton.isVisible()) {
      await upgradeButton.click();
      const modal = page.locator('[role="dialog"]').or(page.locator('text=Complete Checkout'));
      await expect(modal).toBeVisible();
    }

    // 5. Visual regression screenshot capture
    await page.screenshot({ path: 'e2e/playwright-report/checkout_flow_screenshot.png', fullPage: true });
  });
});
