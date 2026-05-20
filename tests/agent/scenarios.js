/**
 * Scenario Library — сценарии для автономного тестера
 * Каждый сценарий = массив шагов {action, target, assert}
 */

export const scenarios = {
  // ═══════════════════════════════════════
  // USER scenarios
  // ═══════════════════════════════════════

  /** Полный флоу: регистрация → покупка */
  fullPurchaseFlow: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]',        value: '{{name}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]',       value: '{{email}}' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]',    value: '{{password}}' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: '{{password}}' },
    { step: 6,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 7,  action: 'assert',    type: 'url',   expected: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 8,  action: 'assert',    type: 'element', selector: '[data-testid="product-card"]', expected: 'visible' },
    { step: 9,  action: 'click',     selector: '[data-testid="product-card"]:first-child' },
    { step: 10, action: 'assert',    type: 'url',   expected: '/product/' },
    { step: 11, action: 'click',     selector: '[data-testid="add-to-cart-button"]' },
    { step: 12, action: 'assert',    type: 'toast', expected: 'Добавлено в корзину' },
    { step: 13, action: 'click',     selector: '[data-testid="cart-link"]' },
    { step: 14, action: 'assert',    type: 'url',   expected: '/cart' },
    { step: 15, action: 'assert',    type: 'element', selector: '[data-testid="cart-item"]', expected: 'visible' },
    // Checkout требует delivery methods — проверяем что кнопка есть
    { step: 16, action: 'assert',    type: 'element', selector: '[data-testid="checkout-button"]', expected: 'visible' },
  ],

  /** Поиск + фильтры */
  searchAndFilter: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'assert',    type: 'element', selector: '[data-testid="search-bar"]', expected: 'visible' },
    { step: 3,  action: 'fill',      selector: '[data-testid="search-bar"]', value: 'айфон' },
    { step: 4,  action: 'wait',      ms: 500 },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="product-card"]', expected: 'visible' },
    { step: 6,  action: 'click',     selector: '[data-testid="category-chip-1"]' },
    { step: 7,  action: 'assert',    type: 'element', selector: '[data-testid="product-card"]', expected: 'visible' },
    { step: 8,  action: 'select',    selector: '[data-testid="sort-select"]', value: 'price_asc' },
    { step: 9,  action: 'wait',      ms: 500 },
    { step: 10, action: 'assert',    type: 'element', selector: '[data-testid="product-card"]', expected: 'visible' },
  ],

  /** Избранное */
  favoritesFlow: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'login',     persona: 'user' },
    { step: 3,  action: 'click',     selector: '[data-testid="product-card"]:first-child [data-testid="favorite-button"]' },
    { step: 4,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/favorites' },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="favorite-item"]', expected: 'visible' },
  ],

  // ═══════════════════════════════════════
  // ADMIN scenarios
  // ═══════════════════════════════════════

  /** Управление категориями */
  adminCategoryManagement: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/login' },
    { step: 2,  action: 'fill',      selector: '[data-testid="login-email"]',    value: '{{email}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="login-password"]', value: '{{password}}' },
    { step: 4,  action: 'click',     selector: '[data-testid="login-submit"]' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 6,  action: 'assert',    type: 'element', selector: '[data-testid="admin-dashboard"]', expected: 'visible' },
    { step: 7,  action: 'click',     selector: '[data-testid="categories-tab"]' },
    { step: 8,  action: 'click',     selector: '[data-testid="add-category-btn"]' },
    { step: 9,  action: 'fill',      selector: '[data-testid="category-name-input"]', value: 'Test Category {{random}}' },
    { step: 10, action: 'click',     selector: '[data-testid="save-category-btn"]' },
    { step: 11, action: 'assert',    type: 'text', selector: 'body', expected: 'Test Category' },
  ],

  /** Управление пользователями */
  adminUserManagement: [
    { step: 1,  action: 'login',     persona: 'admin' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 3,  action: 'click',     selector: '[data-testid="users-tab"]' },
    { step: 4,  action: 'assert',    type: 'element', selector: '[data-testid="users-table"]', expected: 'visible' },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="user-row"]', expected: 'visible' },
  ],

  // ═══════════════════════════════════════
  // SUPPLIER scenarios
  // ═══════════════════════════════════════

  /** Добавление товара */
  supplierAddProduct: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]',        value: '{{name}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]',       value: '{{email}}' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]',    value: '{{password}}' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: '{{password}}' },
    { step: 6,  action: 'select',    selector: '[data-testid="register-role"]', value: 'supplier' },
    { step: 7,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 8,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 9,  action: 'click',     selector: '[data-testid="add-product-btn"]' },
    { step: 10, action: 'fill',      selector: '[data-testid="product-name-input"]',  value: 'Test Product {{random}}' },
    { step: 11, action: 'fill',      selector: '[data-testid="product-price-input"]', value: '9999' },
    { step: 12, action: 'fill',      selector: '[data-testid="product-stock-input"]', value: '10' },
    { step: 13, action: 'click',     selector: '[data-testid="save-product-btn"]' },
    { step: 14, action: 'assert',    type: 'text', selector: 'body', expected: 'Test Product' },
  ],

  /** Редактирование товара */
  supplierEditProduct: [
    { step: 1,  action: 'login',     persona: 'supplier' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 3,  action: 'click',     selector: '[data-testid="edit-product-btn"]:first-child' },
    { step: 4,  action: 'fill',      selector: '[data-testid="product-name-input"]', value: 'Updated Product {{random}}' },
    { step: 5,  action: 'click',     selector: '[data-testid="save-product-btn"]' },
    { step: 6,  action: 'assert',    type: 'text', selector: 'body', expected: 'Updated Product' },
  ],

  // ═══════════════════════════════════════
  // BUG HUNTING scenarios
  // ═══════════════════════════════════════

  /** Проверка доступов — гость не должен видить защищённые страницы */
  unauthorizedAccess: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/cart' },
    { step: 2,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 3,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 4,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 6,  action: 'assert',    type: 'url', expected: '/login' },
  ],

  /** Layout shift проверка — скролл должен быть стабильным */
  layoutStability: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'evaluate',  script: 'document.body.style.overflow = "hidden"' },
    { step: 3,  action: 'screenshot', name: 'homepage-loaded' },
    { step: 4,  action: 'wait',      ms: 3000 },
    { step: 5,  action: 'screenshot', name: 'homepage-stable' },
    { step: 6,  action: 'evaluate',  script: `
      const h1 = document.querySelector('header').getBoundingClientRect().height;
      return h1;
    `, assert: { min: 40, max: 80 } },
  ],
};

/**
 * Получить сценарии для конкретной роли
 */
export function getScenariosForPersona(personaKey) {
  const map = {
    user: ['fullPurchaseFlow', 'searchAndFilter', 'favoritesFlow', 'unauthorizedAccess', 'layoutStability'],
    admin: ['adminCategoryManagement', 'adminUserManagement', 'unauthorizedAccess', 'layoutStability'],
    supplier: ['supplierAddProduct', 'supplierEditProduct', 'unauthorizedAccess', 'layoutStability'],
    all: Object.keys(scenarios),
  };
  const keys = map[personaKey] || map.all;
  return keys.map((k) => ({ name: k, steps: scenarios[k] }));
}
