import { test, expect } from '@playwright/test';
import { goToProfile } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

function createAvatarPng() {
  // 1x1 transparent PNG
  return Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64'
  );
}

async function fillAddress(page, prefix) {
  await page.fill(`[data-testid="${prefix}region"]`, 'Московская область');
  await page.fill(`[data-testid="${prefix}district"]`, 'Одинцовский район');
  await page.fill(`[data-testid="${prefix}city"]`, 'Москва');
  await page.fill(`[data-testid="${prefix}street"]`, 'Ленина');
  await page.fill(`[data-testid="${prefix}house"]`, '15');
  await page.fill(`[data-testid="${prefix}apartment"]`, '42');
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
    await goToProfile(page);
    await expect(page).toHaveURL('/profile');
    await expect(page.locator('[data-testid="profile-email"]')).toBeVisible();

    // Click edit
    await page.click('[data-testid="profile-edit-btn"]');
    await expect(page).toHaveURL('/profile/edit');

    // Edit name and phone (phone is required)
    await page.fill('[data-testid="edit-profile-first-name"]', 'Updated');
    await page.fill('[data-testid="edit-profile-last-name"]', 'Name');
    await page.fill('[data-testid="edit-profile-phone"]', '+79990001122');
    await page.click('[data-testid="edit-profile-save"]');
    await page.waitForTimeout(1000);

    // Go back to profile and verify (displayed as "Last Name First Name")
    await page.goto('/profile');
    await expect(page.locator('.avatar-name')).toContainText('Name Updated');
  });

  test('user can update shipping address', async ({ page }) => {
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

    // Go to edit profile
    await page.goto('/profile/edit');

    // Fill names, phone (required) and shipping address
    await page.fill('[data-testid="edit-profile-first-name"]', 'Адрес');
    await page.fill('[data-testid="edit-profile-last-name"]', 'Тестовый');
    await page.fill('[data-testid="edit-profile-phone"]', '+79990001122');
    await fillAddress(page, 'edit-profile-');
    await page.click('[data-testid="edit-profile-save"]');
    await page.waitForTimeout(1000);

    // Verify saved
    await page.goto('/profile/edit');
    await expect(page.locator('[data-testid="edit-profile-city"]')).toHaveValue('Москва');
    await expect(page.locator('[data-testid="edit-profile-street"]')).toHaveValue('Ленина');
    await expect(page.locator('[data-testid="edit-profile-house"]')).toHaveValue('15');
    await expect(page.locator('[data-testid="edit-profile-apartment"]')).toHaveValue('42');
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
    await page.waitForTimeout(1000);

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

  test('user can upload avatar and see it on profile', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Avatar User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Go to edit profile
    await page.goto('/profile/edit');

    // Upload avatar
    const fileInput = page.locator('.edit-card--avatar input[type="file"]');
    await fileInput.setInputFiles({
      name: 'avatar.png',
      mimeType: 'image/png',
      buffer: createAvatarPng(),
    });

    // Wait for success toast and preview update
    await expect(page.locator('[data-testid="toast-message"]')).toContainText('Фото профиля обновлено', { timeout: 10000 });
    await expect(page.locator('.avatar-preview__img')).toBeVisible();

    // Verify avatar persists on profile page after reload
    await page.goto('/profile');
    await expect(page.locator('.avatar__img')).toBeVisible();
  });
});
