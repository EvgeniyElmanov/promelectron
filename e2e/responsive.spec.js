import { test, expect } from '@playwright/test';

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
