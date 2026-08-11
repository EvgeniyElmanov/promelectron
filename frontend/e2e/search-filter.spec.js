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
    await searchBar.fill('ВВГнг');

    // Wait for debounce (300ms) + network
    await page.waitForTimeout(600);

    // Should show only ВВГ-cables (электрокаталог, issue #147; на test-стенде
    // каталог дополнительно содержит товары onec-мока — точное число не фиксируем)
    const cards = page.locator('[data-testid="product-card"]');
    await expect(cards.first()).toBeVisible();
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      await expect(cards.nth(i)).toContainText(/ВВГ/);
    }
  });

  test('category filter shows only products from selected category', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="category-chips"]')).toBeVisible();

    // Wait for categories and products to load
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
    // Scope к chips: в meilisearch-режиме название категории есть и в FilterPanel.
    const socketChip = page.locator('[data-testid="category-chips"]').getByText('Розетки');
    await expect(socketChip).toBeVisible({ timeout: 10000 });

    // Count all products before filter
    const allCards = page.locator('[data-testid="product-card"]');
    const allCount = await allCards.count();
    expect(allCount).toBeGreaterThan(2);

    // Click "Розетки" category
    await socketChip.click();
    await page.waitForTimeout(400);

    // Should show only socket products
    const socketCards = page.locator('[data-testid="product-card"]');
    const socketCount = await socketCards.count();
    expect(socketCount).toBeLessThan(allCount);

    // Verify all visible cards contain socket-related text
    for (let i = 0; i < socketCount; i++) {
      await expect(socketCards.nth(i)).toContainText(/Розетка/);
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

    // Set price range 500 - 5000 (диапазон цен электрокаталога, issue #147)
    if (flagOn) {
      // meilisearch-режим: фильтр цены в FilterPanel
      await page.fill('[data-testid="filter-price-min"]', '500');
      await page.fill('[data-testid="filter-price-max"]', '5000');
      await page.click('[data-testid="filter-apply"]');
    } else {
      await page.fill('[data-testid="min-price-input"]', '500');
      await page.fill('[data-testid="max-price-input"]', '5000');
      await page.click('[data-testid="apply-price-btn"]');
    }

    // Wait for the filter to apply (prices may update asynchronously)
    await expect(async () => {
      const prices = await page.locator('[data-testid="product-card"] [data-testid="product-price"]').allTextContents();
      expect(prices.length).toBeGreaterThan(0);
      for (const priceText of prices) {
        const price = parsePrice(priceText);
        expect(price).toBeGreaterThanOrEqual(500);
        expect(price).toBeLessThanOrEqual(5000);
      }
    }).toPass({ timeout: 5000 });
  });
});
