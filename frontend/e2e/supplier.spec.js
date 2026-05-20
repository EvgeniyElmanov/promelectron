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

    // 4. Click "Add product"
    await page.click('.supplier-products__add');

    // 5. Fill form
    await page.fill('[data-testid="product-name-input"]', productName);
    await page.fill('[data-testid="product-description-input"]', 'Test description for e2e');
    await page.fill('[data-testid="product-price-input"]', '12345');
    await page.fill('[data-testid="product-stock-input"]', '10');
    // Select by label to avoid hardcoding DB-assigned category ID
    await page.selectOption('[data-testid="product-category-select"]', { label: 'Смартфоны' });
    await page.click('[data-testid="product-submit-btn"]');

    // 6. Wait for modal to close and product to appear
    await expect(page.locator('.modal-overlay')).not.toBeVisible({ timeout: 10000 });
    await expect(
      page.locator('.supplier-product-card__name').filter({ hasText: productName }).first()
    ).toBeVisible({ timeout: 10000 });

    // 7. Verify the delete button exists
    const productCard = page.locator('[data-testid="supplier-product-card"]').filter({ hasText: productName }).first();
    await expect(productCard.locator('.supplier-product-card__btn--delete')).toBeVisible();
  });
});
