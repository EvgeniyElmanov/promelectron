import { test, expect } from '@playwright/test';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

function parsePrice(text) {
  return parseFloat(text.replace('₽', '').replace(/\s/g, '').replace(',', '.'));
}

test.describe('Search & Filters', () => {
  // В meilisearch-режиме (feature flag catalog_search_meilisearch) часть
  // legacy-контролов скрыта, а тексты категорий дублируются в FilterPanel —
  // селекторы зависят от режима.
  let flagOn = false;

  test.beforeAll(async ({ request }) => {
    const probe = await request.get('/api/v1/search/', {
      params: { page: 1, hits_per_page: 1 },
    });
    flagOn = probe.status() === 200;
  });

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
    // Scope к chips: в meilisearch-режиме название категории есть и в FilterPanel.
    const laptopChip = page.locator('[data-testid="category-chips"]').getByText('Ноутбуки');
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

    // Extract prices and verify ascending order (ждём применения сортировки)
    await expect(async () => {
      const prices = await page.locator('[data-testid="product-card"] [data-testid="product-price"]').allTextContents();
      const numericPrices = prices.map(parsePrice);
      expect(numericPrices.length).toBeGreaterThan(0);
      for (let i = 1; i < numericPrices.length; i++) {
        expect(numericPrices[i]).toBeGreaterThanOrEqual(numericPrices[i - 1]);
      }
    }).toPass({ timeout: 10000 });
  });

  test('price range filter', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Set price range 20000 - 50000
    if (flagOn) {
      // meilisearch-режим: фильтр цены в FilterPanel
      await page.fill('[data-testid="filter-price-min"]', '20000');
      await page.fill('[data-testid="filter-price-max"]', '50000');
      await page.click('[data-testid="filter-apply"]');
    } else {
      await page.fill('[data-testid="min-price-input"]', '20000');
      await page.fill('[data-testid="max-price-input"]', '50000');
      await page.click('[data-testid="apply-price-btn"]');
    }

    // Wait for the filter to apply (prices may update asynchronously)
    await expect(async () => {
      const prices = await page.locator('[data-testid="product-card"] [data-testid="product-price"]').allTextContents();
      expect(prices.length).toBeGreaterThan(0);
      for (const priceText of prices) {
        const price = parsePrice(priceText);
        expect(price).toBeGreaterThanOrEqual(20000);
        expect(price).toBeLessThanOrEqual(50000);
      }
    }).toPass({ timeout: 5000 });
  });
});
