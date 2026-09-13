import { test, expect } from '@playwright/test';

const GUEST_CART_ITEM = {
  product_id: 1,
  quantity: 2,
  name: 'Test Product',
  price: 4999,
  stock: 10,
  images: [],
};

const viewports = [
  { width: 320, height: 568, name: 'mobile-xs' },
  { width: 375, height: 667, name: 'mobile' },
  { width: 768, height: 1024, name: 'tablet' },
  { width: 1024, height: 768, name: 'tablet-landscape' },
  { width: 1280, height: 720, name: 'desktop' },
  { width: 1920, height: 1080, name: 'desktop-hd' },
  { width: 2560, height: 1440, name: 'desktop-qhd' },
  { width: 3840, height: 2160, name: 'desktop-4k' },
];

const pages = [
  { path: '/', name: 'homepage' },
  { path: '/login', name: 'login' },
  { path: '/register', name: 'register' },
  { path: '/cart', name: 'cart' },
  { path: '/product/1', name: 'product-detail' },
  { path: '/profile', name: 'profile' },
  { path: '/orders', name: 'orders' },
  { path: '/favorites', name: 'favorites' },
];

for (const vp of viewports) {
  test.describe(`Responsive @ ${vp.name} (${vp.width}x${vp.height})`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });

    for (const pageInfo of pages) {
      test(`no horizontal scroll on ${pageInfo.name}`, async ({ page }) => {
        await page.goto(pageInfo.path);
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(500);

        const hasHorizontalScroll = await page.evaluate(() => {
          return document.documentElement.scrollWidth > document.documentElement.clientWidth;
        });

        expect(hasHorizontalScroll, `Horizontal scroll detected at ${vp.width}x${vp.height} on ${pageInfo.name}`).toBe(false);
      });
    }
  });
}

test.describe('Mobile header cleanup', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('mobile header shows [Menu][Logo][Cart] and mobile search, hides desktop actions', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // §11 mobile: компоновка [Menu][Logo][Cart] + строка поиска (issue #250, D-05).
    await expect(page.locator('[data-testid="mobile-menu-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="header-logo"]')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-cart-link"]')).toBeVisible();
    await expect(page.locator('[data-testid="header-search-bar-mobile"]')).toBeVisible();

    // Desktop-действия скрыты.
    await expect(page.locator('.header__actions')).toBeHidden();
    await expect(page.locator('[data-testid="cart-link"]')).toBeHidden();
    await expect(page.locator('[data-testid="profile-link"]')).toBeHidden();
    await expect(page.locator('[data-testid="login-link"]')).toBeHidden();
  });

  test('mobile menu drawer opens and closes', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.locator('[data-testid="mobile-menu-btn"]').click();
    const drawer = page.locator('[data-testid="mobile-menu-drawer"]');
    await expect(drawer).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(drawer).toBeHidden();
  });

  test('header still shows all action icons on desktop', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.header__actions')).toBeVisible();
    await expect(page.locator('[data-testid="cart-link"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-link"]')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-menu-btn"]')).toBeHidden();
    await expect(page.locator('[data-testid="mobile-cart-link"]')).toBeHidden();
  });
});

test.describe('Mobile bottom navigation cart badge', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('cart badge is positioned at the top-right of the cart icon', async ({ page }) => {
    await page.goto('/');
    await page.evaluate((item) => {
      localStorage.setItem('guest_cart', JSON.stringify([item]));
    }, GUEST_CART_ITEM);
    await page.reload();
    await page.waitForLoadState('networkidle');

    const badge = page.locator('[data-testid="nav-Корзина"] .bottom-nav__badge');
    await expect(badge).toBeVisible();
    await expect(badge).toHaveText('2');

    const icon = page.locator('[data-testid="nav-Корзина"] .bottom-nav__icon');
    const badgeBox = await badge.boundingBox();
    const iconBox = await icon.boundingBox();
    expect(badgeBox).not.toBeNull();
    expect(iconBox).not.toBeNull();

    // Badge center should be to the right of the icon center
    const badgeCenterX = badgeBox.x + badgeBox.width / 2;
    const iconCenterX = iconBox.x + iconBox.width / 2;
    expect(badgeCenterX).toBeGreaterThan(iconCenterX);

    // Badge top should be at or above the icon top
    expect(badgeBox.y).toBeLessThanOrEqual(iconBox.y + 2);
  });
});
