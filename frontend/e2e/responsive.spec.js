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

// gh-258: регрессионные проверки адаптивных дефектов.
test.describe('Adaptive layout gh-258', () => {
  const contentPages = ['/', '/product/1', '/cart', '/login'];

  test.describe('360px: bottom nav не перекрывает контент в конце скролла', () => {
    test.use({ viewport: { width: 360, height: 800 } });
    for (const path of contentPages) {
      test(path, async ({ page }) => {
        await page.goto(path);
        await page.waitForLoadState('networkidle');
        const gap = await page.evaluate(() => {
          window.scrollTo(0, document.body.scrollHeight);
          const app = document.querySelector('.desktop-container');
          const nav = document.querySelector('.bottom-nav');
          if (!app || !nav || getComputedStyle(nav).display === 'none') return Infinity;
          return nav.getBoundingClientRect().top - app.getBoundingClientRect().bottom;
        });
        // Допуск 1px на субпиксельное округление getBoundingClientRect.
        expect(gap, `контент ${path} перекрыт bottom nav в конце скролла`).toBeGreaterThanOrEqual(-1);
      });
    }
  });

  test('768px: шапка в мобильном режиме, bottom nav виден', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('[data-testid="mobile-menu-btn"]')).toBeVisible();
    await expect(page.locator('.header__actions')).toBeHidden();
    await expect(page.locator('.bottom-nav')).toBeVisible();

    // gh-258 F001: на планшете бургер должен открывать видимый drawer.
    await page.locator('[data-testid="mobile-menu-btn"]').click();
    await expect(page.locator('[data-testid="mobile-menu-drawer"]')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('1024px: шапка десктопная и в одной строке', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.header__actions')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-menu-btn"]')).toBeHidden();
    await expect(page.locator('.bottom-nav')).toBeHidden();
    const headerHeight = await page.locator('.header').evaluate((el) => el.getBoundingClientRect().height);
    expect(headerHeight).toBeLessThanOrEqual(73);
  });

  test('1920px: сетка каталога использует ширину (wide-контейнер, резиновые карточки)', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // До фикса #258 контейнер был ~1200px, сетка ~900px. Число колонок не проверяем:
    // оно зависит от сайдбара фильтров и gap, ширина используется через 1fr-растяжение.
    const gridWidth = await page.locator('.home__grid').evaluate(
      (el) => el.getBoundingClientRect().width,
    );
    expect(gridWidth, 'сетка на 1920 должна быть заметно шире доковой (~900px)').toBeGreaterThan(1200);
    const cardWidth = await page.locator('.home__grid > :first-child').evaluate(
      (el) => el.getBoundingClientRect().width,
    );
    expect(cardWidth, 'карточки должны растягиваться за пределы минимума minmax (220px)').toBeGreaterThan(220);
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
