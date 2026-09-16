import { test, expect } from '@playwright/test';

// Витрина главной (D-02…D-11, issue #263): структура секций по макету,
// входы в каталог ведут на /catalog, таб «Скидки» — честный empty-state.
// Тексты/имена категорий из 1С-дампа не фиксируем — только testid и структура.

test.describe('Home storefront', () => {
  test('desktop: все секции витрины на месте, инлайн-каталога нет', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    await expect(page.locator('[data-testid="hero-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="hero-cta-laptops"]')).toBeVisible();
    await expect(page.locator('[data-testid="promo-stack"]')).toBeVisible();
    await expect(page.locator('[data-testid="benefits-strip"]')).toBeVisible();
    await expect(page.locator('[data-testid="popular-categories"]')).toBeVisible();
    await expect(page.locator('[data-testid="popular-products"]')).toBeVisible();
    await expect(page.locator('[data-testid="home-consultation"]')).toBeVisible();
    await expect(page.locator('[data-testid="app-footer"]')).toBeVisible();
    await expect(page.locator('[data-testid="category-nav"]')).toBeVisible();
    await expect(page.locator('[data-testid="catalog-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="compare-link"]')).toBeVisible();

    // Каталога с фильтрами на главной нет
    await expect(page.locator('[data-testid="sort-select"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="filter-panel"]')).toHaveCount(0);
  });

  test('hero CTA ведёт на /catalog', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.locator('[data-testid="hero-cta-laptops"]').click();
    await expect(page).toHaveURL(/\/catalog/);
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  });

  test('клик по карточке категории ведёт на /catalog?category_id=', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    const firstCategory = page.locator('[data-testid^="category-card-"]').first();
    await expect(firstCategory).toBeVisible();
    await firstCategory.click();
    await expect(page).toHaveURL(/\/catalog\?category_id=\d+/);
  });

  test('категорийная навигация ведёт в каталог; «Распродажа» — на таб «Скидки»', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');

    const firstNavLink = page.locator('[data-testid^="category-nav-link-"]').first();
    await expect(firstNavLink).toBeVisible();
    await firstNavLink.click();
    await expect(page).toHaveURL(/\/catalog\?category_id=\d+/);

    await page.goto('/');
    await page.locator('[data-testid="category-nav-sale"]').click();
    await expect(page).toHaveURL(/\/\?tab=sale/);
    await expect(page.locator('[data-testid="products-tab-sale-empty"]')).toBeVisible();
  });

  test('табы популярных товаров переключают выборку; «Скидки» — empty-state', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('[data-testid="products-tab-hits"]')).toBeVisible();
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    await page.locator('[data-testid="products-tab-new"]').click();
    await expect(page.locator('[data-testid="products-tab-new"]')).toHaveAttribute('aria-selected', 'true');
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    await page.locator('[data-testid="products-tab-sale"]').click();
    await expect(page.locator('[data-testid="products-tab-sale-empty"]')).toContainText('Скидок сейчас нет');
  });

  test('поиск из шапки ведёт на /catalog?q=', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/');
    await page.locator('[data-testid="header-search-bar"]').fill('ВВГнг');
    await page.locator('[data-testid="header-search-bar"]').press('Enter');
    await expect(page).toHaveURL(/\/catalog\?q=/);
  });

  test('редирект /?q= → /catalog?q= (D-02)', async ({ page }) => {
    await page.goto('/?q=ВВГнг');
    await expect(page).toHaveURL(/\/catalog\?q=/);
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();
  });

  test('mobile 375px: stacked layout, промо и category-nav скрыты, товары 2 колонки', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    await expect(page.locator('[data-testid="hero-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="promo-stack"]')).toBeHidden();
    await expect(page.locator('[data-testid="category-nav"]')).toBeHidden();
    await expect(page.locator('[data-testid="popular-categories"]')).toBeVisible();
    await expect(page.locator('[data-testid="product-card"]').first()).toBeVisible();

    // Нет горизонтального скролла
    const hasHorizontalScroll = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(hasHorizontalScroll).toBe(false);
  });
});
