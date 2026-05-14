import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}@example.com`;
}

test.describe('Profile & Edit Profile', () => {
  test('user can view profile and edit name', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Go to profile
    await page.click('[data-testid="profile-link"]');
    await expect(page).toHaveURL('/profile');
    await expect(page.locator('[data-testid="profile-email"]')).toBeVisible();

    // Click edit
    await page.click('[data-testid="profile-edit-btn"]');
    await expect(page).toHaveURL('/profile/edit');

    // Edit name
    await page.fill('[data-testid="edit-profile-name"]', 'Updated Name');
    await page.click('[data-testid="edit-profile-save"]');

    // Go back to profile and verify
    await page.goto('/profile');
    await expect(page.locator('.avatar-name')).toContainText('Updated Name');
  });

  test('user can change password', async ({ page }) => {
    const email = uniqueEmail();
    const oldPassword = 'TestPassword123!';
    const newPassword = 'NewPassword456!';

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', oldPassword);
    await page.fill('[data-testid="register-password-confirm"]', oldPassword);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Go to edit profile
    await page.goto('/profile/edit');

    // Change password
    await page.fill('[data-testid="edit-profile-old-password"]', oldPassword);
    await page.fill('[data-testid="edit-profile-new-password"]', newPassword);
    await page.fill('[data-testid="edit-profile-confirm-password"]', newPassword);
    await page.click('[data-testid="edit-profile-password-save"]');

    // Logout
    await page.goto('/profile');
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL('/login');

    // Login with new password
    await page.fill('[data-testid="login-email"]', email);
    await page.fill('[data-testid="login-password"]', newPassword);
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');
  });
});
