export async function goToCart(page) {
  const headerLink = page.locator('[data-testid="cart-link"]');
  const bottomNavItem = page.locator('[data-testid="nav-Корзина"]');
  if (await headerLink.isVisible().catch(() => false)) {
    await headerLink.click();
  } else {
    await bottomNavItem.click();
  }
}

export async function goToProfile(page) {
  const headerLink = page.locator('[data-testid="profile-link"]');
  const bottomNavItem = page.locator('[data-testid="nav-Профиль"]');
  if (await headerLink.isVisible().catch(() => false)) {
    await headerLink.click();
  } else {
    await bottomNavItem.click();
  }
}
