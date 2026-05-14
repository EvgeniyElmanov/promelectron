import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}@example.com`;
}

test.describe('Search & Filters', () => {
  test('search filters products by name', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="search-bar"]')).toBeVisible();

    // Wait for products to load
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    const searchBar = page.locator('[data-testid="search-bar"]');
    await searchBar.fill('Nova');

    // Wait for debounce (300ms) + network
    await page.waitForTimeout(600);

    // Should show only the Nova X12 smartphone
    const cards = page.locator('[data-testid="product-card"]');
    await expect(cards).toHaveCount(1);
    await expect(cards.first()).toContainText('Nova X12');
  });

  test('category filter shows only products from selected category', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="category-chips"]')).toBeVisible();

    // Wait for categories and products to load
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
    const laptopChip = page.getByText('Ноутбуки');
    await expect(laptopChip).toBeVisible({ timeout: 10000 });

    // Count all products before filter
    const allCards = page.locator('[data-testid="product-card"]');
    const allCount = await allCards.count();
    expect(allCount).toBeGreaterThan(2);

    // Click "Ноутбуки" category
    await laptopChip.click();
    await page.waitForTimeout(400);

    // Should show only laptop products
    const laptopCards = page.locator('[data-testid="product-card"]');
    const laptopCount = await laptopCards.count();
    expect(laptopCount).toBeLessThan(allCount);

    // Verify all visible cards contain laptop-related text
    for (let i = 0; i < laptopCount; i++) {
      await expect(laptopCards.nth(i)).toContainText(/Ноутбук|Orion|Falcon/);
    }
  });

  test('sort by price ascending', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Select price ascending
    const sortSelect = page.locator('[data-testid="sort-select"]');
    await sortSelect.selectOption('price_asc');
    await page.waitForTimeout(400);

    // Extract prices and verify ascending order
    const prices = await page.locator('[data-testid="product-card"] [data-testid="product-price"]').allTextContents();
    const numericPrices = prices.map(p => parseFloat(p.replace(/[^\d.]/g, '')));

    for (let i = 1; i < numericPrices.length; i++) {
      expect(numericPrices[i]).toBeGreaterThanOrEqual(numericPrices[i - 1]);
    }
  });

  test('price range filter', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Set price range 20000 - 50000
    await page.fill('[data-testid="min-price-input"]', '20000');
    await page.fill('[data-testid="max-price-input"]', '50000');
    await page.click('[data-testid="apply-price-btn"]');
    await page.waitForTimeout(400);

    // Verify all visible products are within range
    const prices = await page.locator('[data-testid="product-card"] [data-testid="product-price"]').allTextContents();
    for (const priceText of prices) {
      const price = parseFloat(priceText.replace(/[^\d.]/g, ''));
      expect(price).toBeGreaterThanOrEqual(20000);
      expect(price).toBeLessThanOrEqual(50000);
    }
  });
});
