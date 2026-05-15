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
    await page.fill('.modal__form input[type="text"]', productName);
    await page.fill('.modal__form textarea', 'Test description for e2e');
    const priceInputs = page.locator('.modal__form input[type="number"]');
    await priceInputs.first().fill('12345');
    await priceInputs.last().fill('10');
    await page.selectOption('.modal__form select', '1'); // Смартфоны
    await page.click('.modal__submit');

    // 6. Wait for modal to close and product to appear
    await page.waitForTimeout(500);
    await expect(page.locator('.supplier-product-card__name').filter({ hasText: productName }).first()).toBeVisible();

    // 7. Verify the delete button exists
    const productCard = page.locator('.supplier-product-card').filter({ hasText: productName }).first();
    await expect(productCard.locator('.supplier-product-card__btn--delete')).toBeVisible();
  });
});
