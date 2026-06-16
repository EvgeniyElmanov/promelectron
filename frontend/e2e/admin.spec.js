import { test, expect } from '@playwright/test';

test.describe('Admin Panel', () => {
  test('admin can navigate between section tabs', async ({ page }) => {
    // 1. Login as admin
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');

    // 2. Navigate to admin page via profile
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible();
    await page.click('[data-testid="profile-admin-link"]');
    await expect(page).toHaveURL('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();

    // 3. Dashboard is active by default
    await expect(page.locator('[data-testid="admin-section-tab-dashboard"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('.admin__section-title:has-text("Заказы за 7 дней")')).toBeVisible();

    // 4. Switch to Users tab
    await page.click('[data-testid="admin-section-tab-users"]');
    await expect(page.locator('[data-testid="admin-section-tab-users"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('.admin__section-title:has-text("Пользователи")')).toBeVisible();
    await expect(page.locator('.admin__section-title:has-text("Заказы за 7 дней")')).not.toBeVisible();

    // 5. Switch to Categories tab
    await page.click('[data-testid="admin-section-tab-categories"]');
    await expect(page.locator('[data-testid="admin-section-tab-categories"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('[data-testid="categories-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="add-category-btn"]')).toBeVisible();

    // 6. Switch to Delivery tab
    await page.click('[data-testid="admin-section-tab-delivery"]');
    await expect(page.locator('[data-testid="admin-section-tab-delivery"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('.admin__section-title:has-text("Способы доставки")')).toBeVisible();

    // 7. Switch to Orders tab
    await page.click('[data-testid="admin-section-tab-orders"]');
    await expect(page.locator('[data-testid="admin-section-tab-orders"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('.admin__section-title:has-text("Заказы")')).toBeVisible();

    // 8. Switch to Feature Flags tab
    await page.click('[data-testid="admin-section-tab-feature-flags"]');
    await expect(page.locator('[data-testid="admin-section-tab-feature-flags"]')).toHaveClass(/admin__tab--active/);
    await expect(page.locator('.admin__section-title:has-text("Фичатоглы")')).toBeVisible();
  });

  test('admin can view admin page and categories table', async ({ page }) => {
    // 1. Login as admin
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');

    // 2. Navigate to admin page via profile
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible();
    await page.click('[data-testid="profile-admin-link"]');
    await expect(page).toHaveURL('/admin');
    await expect(page.locator('[data-testid="admin-page"]')).toBeVisible();

    // 3. Switch to Categories tab
    await page.click('[data-testid="admin-section-tab-categories"]');

    // 4. Create a test category
    await page.click('[data-testid="add-category-btn"]');
    await page.fill('[data-testid="category-name-input"]', 'E2E Test Category');
    await page.fill('[data-testid="category-description-input"]', 'Test description');
    await page.click('[data-testid="category-submit-btn"]');

    // 5. Wait for modal to close, then verify category appears in table
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });
    const categoryRow = page.locator('.admin__table tr').filter({ hasText: 'E2E Test Category' }).first();
    await expect(categoryRow).toBeVisible({ timeout: 10000 });

    // 6. Verify "Add" button exists
    await expect(page.locator('[data-testid="add-category-btn"]')).toBeVisible();

    // 7. Cleanup: delete the test category
    page.once('dialog', (dialog) => dialog.accept());
    await categoryRow.locator('.admin__icon-btn--delete').click();
    await expect(categoryRow).not.toBeVisible({ timeout: 10000 });
  });

  test('admin can create root category and subcategory, switch tab and verify visibility', async ({ page }) => {
    const rootName = 'E2E Root Category';
    const childName = 'E2E Child Category';

    // 1. Login as admin
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-admin@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');

    // 2. Navigate to admin page
    await page.goto('/profile');
    await page.click('[data-testid="profile-admin-link"]');
    await expect(page).toHaveURL('/admin');

    // 3. Switch to Categories tab
    await page.click('[data-testid="admin-section-tab-categories"]');

    // 4. Create root category
    await page.click('[data-testid="add-category-btn"]');
    await page.fill('[data-testid="category-name-input"]', rootName);
    await page.fill('[data-testid="category-description-input"]', 'Root test description');
    await page.selectOption('[data-testid="category-parent-select"]', { label: 'Без родителя' });
    await page.click('[data-testid="category-submit-btn"]');
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });

    const rootRow = page.locator('.admin__table tr').filter({ hasText: rootName }).first();
    await expect(rootRow).toBeVisible({ timeout: 10000 });

    // 5. Create subcategory
    await page.click('[data-testid="add-category-btn"]');
    await page.fill('[data-testid="category-name-input"]', childName);
    await page.fill('[data-testid="category-description-input"]', 'Child test description');
    await page.selectOption('[data-testid="category-parent-select"]', { label: rootName });
    await page.click('[data-testid="category-submit-btn"]');
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });

    const childRow = page.locator('.admin__table tr').filter({ hasText: childName }).first();
    await expect(childRow).toBeVisible({ timeout: 10000 });

    // 6. Switch to root category tab
    const rootTab = page.locator('.admin__category-tab').filter({ hasText: rootName }).first();
    await expect(rootTab).toBeVisible({ timeout: 10000 });
    await rootTab.click();

    // 7. Verify subcategory is visible and root category is not in the table
    await expect(childRow).toBeVisible({ timeout: 10000 });
    await expect(rootRow).not.toBeVisible({ timeout: 10000 });

    // 8. Cleanup: delete both categories
    page.once('dialog', (dialog) => dialog.accept());
    await childRow.locator('.admin__icon-btn--delete').click();
    await expect(childRow).not.toBeVisible({ timeout: 10000 });

    // Return to "All" tab to delete root
    await page.click('[data-testid="category-tab-all"]');
    await expect(rootRow).toBeVisible({ timeout: 10000 });
    page.once('dialog', (dialog) => dialog.accept());
    await rootRow.locator('.admin__icon-btn--delete').click();
    await expect(rootRow).not.toBeVisible({ timeout: 10000 });
  });
});
