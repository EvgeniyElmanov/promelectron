import { test, expect } from '@playwright/test';
import { goToCart, getInStockProductCard, openFiltersPanel } from './helpers.js';

function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}

test.describe('Catalog & Cart', () => {
  test('homepage shows products and categories', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="search-bar"]')).toBeVisible();
    await expect(page.locator('[data-testid="category-chips"]')).toBeVisible();
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  });

  test('product can be added to cart', async ({ page }) => {
    const email = uniqueEmail();
    const password = 'TestPassword123!';

    // Register first
    await page.goto('/register');
    await page.fill('[data-testid="register-name"]', 'Test User');
    await page.fill('[data-testid="register-email"]', email);
    await page.fill('[data-testid="register-password"]', password);
    await page.fill('[data-testid="register-password-confirm"]', password);
    await page.click('[data-testid="register-submit"]');
    await expect(page).toHaveURL('/');

    // Add product to cart
    const firstProduct = await getInStockProductCard(page);
    await firstProduct.locator('[data-testid="add-to-cart-button"]').click();
    // Wait for in-cart button state (success toast removed, D-04)
    await expect(firstProduct.locator('[data-testid="add-to-cart-button"]')).toContainText('В корзине', { timeout: 5000 });

    // Go to cart
    await goToCart(page);
    await expect(page).toHaveURL('/cart');
    await page.waitForSelector('[data-testid="cart-item"]', { timeout: 5000 });
  });
});

test.describe('Facet filters (feature flag catalog_search_meilisearch)', () => {
  let flagOn = false;

  test.beforeAll(async ({ request }) => {
    // Probe: флаг выключен → 404, весь describe скипается (D-07, E2E не краснеет).
    const probe = await request.get('/api/v1/search/', {
      params: { page: 1, hits_per_page: 1 },
    });
    flagOn = probe.status() === 200;
  });

  test.beforeEach(async ({}, testInfo) => {
    testInfo.skip(!flagOn, 'feature flag catalog_search_meilisearch выключен на этом окружении');
  });

  test('выбор значения фасета фильтрует выдачу, URL отражает фильтр, counts не обнуляются', async ({ page }) => {
    await page.goto('/');
    await openFiltersPanel(page);
    await expect(page.locator('[data-testid="filter-panel"]')).toBeVisible();

    const firstValue = page.locator('[data-testid^="filter-value-"]').first();
    await expect(firstValue).toBeVisible();
    const group = firstValue.locator('xpath=ancestor::*[@data-testid and starts-with(@data-testid, "filter-group-")][1]');
    const valuesCount = await group.locator('[data-testid^="filter-value-"]').count();

    await firstValue.click();
    await expect(page).toHaveURL(/attr\./);
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Disjunctive-счётчики: остальные значения группы не обнулились
    const otherCounts = await group.locator('.filter-panel__count').allTextContents();
    expect(otherCounts.some((text) => !text.includes('(0)'))).toBe(true);
    expect(valuesCount).toBeGreaterThan(0);
  });

  test('перезагрузка по URL восстанавливает состояние фильтров', async ({ page }) => {
    await page.goto('/');
    await openFiltersPanel(page);
    await expect(page.locator('[data-testid="filter-panel"]')).toBeVisible();

    const firstValue = page.locator('[data-testid^="filter-value-"]').first();
    await firstValue.click();
    await expect(page).toHaveURL(/attr\./);

    const url = page.url();
    await page.goto(url);
    await openFiltersPanel(page);
    await expect(page.locator('[data-testid="filter-panel"]')).toBeVisible();
    await expect(page.locator('[data-testid^="filter-value-"]').first()).toBeChecked();
  });

  test('фильтр цены шлёт price_min/price_max в URL', async ({ page }) => {
    await page.goto('/');
    await openFiltersPanel(page);
    await expect(page.locator('[data-testid="filter-price-min"]')).toBeVisible();

    await page.fill('[data-testid="filter-price-min"]', '1000');
    await page.fill('[data-testid="filter-price-max"]', '5000');
    await page.click('[data-testid="filter-apply"]');

    await expect(page).toHaveURL(/price_min=1000/);
    await expect(page).toHaveURL(/price_max=5000/);
  });

  test('filter-reset сбрасывает фильтры и URL', async ({ page }) => {
    await page.goto('/');
    await openFiltersPanel(page);
    await expect(page.locator('[data-testid="filter-panel"]')).toBeVisible();

    await page.locator('[data-testid^="filter-value-"]').first().click();
    await expect(page).toHaveURL(/attr\./);

    await page.click('[data-testid="filter-reset"]');
    await expect(page).not.toHaveURL(/attr\./);
  });
});

test.describe('Catalog listing без feature flag', () => {
  test('при выключенном флаге (404 probe) FilterPanel отсутствует, листинг работает как раньше', async ({ page, request }) => {
    const probe = await request.get('/api/v1/search/', {
      params: { page: 1, hits_per_page: 1 },
    });
    test.skip(probe.status() !== 404, 'feature flag включён — legacy-режим не проверяем');

    await page.goto('/');
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
    await expect(page.locator('[data-testid="filter-panel"]')).toHaveCount(0);
    // legacy-фильтры на месте
    await expect(page.locator('[data-testid="rating-filter-1"]')).toBeVisible();
  });
});
