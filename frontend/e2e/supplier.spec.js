import { test, expect } from '@playwright/test';

test.describe('Supplier Products', () => {
  test('supplier can create and delete a product', async ({ page }) => {
    const productName = `E2E Product ${Date.now()}`;

    // 1. Login as seed supplier
    await page.goto('/login');
    await page.fill('[data-testid="login-email"]', 'seed-supplier@example.com');
    await page.fill('[data-testid="login-password"]', 'seedpassword123');
    await page.click('[data-testid="login-submit"]');
    await expect(page).toHaveURL('/');

    // 2. Go to profile and click "Мои товары"
    await page.goto('/profile');
    await expect(page.locator('[data-testid="profile-page"]')).toBeVisible();
    await page.click('[data-testid="profile-supplier-link"]');
    await expect(page).toHaveURL('/my-products');
    await expect(page.locator('[data-testid="supplier-products"]')).toBeVisible();

    // 3. Click "Add product"
    await page.click('.supplier-products__add');

    // 4. Fill form
    await page.fill('[data-testid="product-name-input"]', productName);
    await page.fill('[data-testid="product-description-input"]', 'Test description for e2e');
    await page.fill('[data-testid="product-price-input"]', '12345');
    await page.fill('[data-testid="product-stock-input"]', '10');
    // Select by label to avoid hardcoding DB-assigned category ID
    await page.selectOption('[data-testid="product-category-select"]', { label: 'Смартфоны' });
    await page.click('[data-testid="product-submit-btn"]');

    // 5. Wait for modal to close and product to appear
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });
    const productCard = page.locator('[data-testid="supplier-product-card"]').filter({ hasText: productName }).first();
    await expect(productCard).toBeVisible({ timeout: 10000 });

    // 6. Verify the delete button exists
    const deleteBtn = productCard.locator('.supplier-product-card__btn--delete');
    await expect(deleteBtn).toBeVisible();

    // 7. Cleanup: delete (deactivate) the test product
    page.once('dialog', (dialog) => dialog.accept());
    await deleteBtn.click();
    await expect(productCard.locator('.supplier-product-card__badge')).toHaveText('Неактивен', { timeout: 10000 });
  });
});
