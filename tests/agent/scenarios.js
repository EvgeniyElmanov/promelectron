/**
 * Scenario Library — полная библиотека сценариев для автономного тестера
 * 
 * Селекторы:
 *   - data-testid: предпочтительный вариант
 *   - text=Label: Playwright MCP text-based selector
 *   - ref=e28: Playwright MCP accessibility ref
 *   - CSS селекторы: стандартные
 * 
 * Категории:
 *   USER: покупка, поиск, избранное, профиль, отзывы, заказы
 *   ADMIN: категории, пользователи, заказы, доставка, статистика
 *   SUPPLIER: товары, заказы, профиль
 *   SECURITY: доступы, валидация, инъекции
 *   PERFORMANCE: скорость, layout stability, метрики
 *   CROSS-ROLE: сквозные сценарии через несколько ролей
 *   FUZZ: случайные данные, edge cases
 *   ACCESSIBILITY: a11y проверки
 *   RESPONSIVE: мобильные/десктоп breakpoints
 */

export const scenarios = {
  // ═══════════════════════════════════════════════════
  // USER scenarios — Покупатель
  // ═══════════════════════════════════════════════════

  /** Полный флоу: регистрация → покупка */
  fullPurchaseFlow: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]',        value: '{{name}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]',       value: '{{email}}' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]',    value: '{{password}}' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: '{{password}}' },
    { step: 6,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 7,  action: 'assert',    type: 'url',   expected: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 8,  action: 'assert',    type: 'element', selector: 'text=Популярные товары', expected: 'visible' },
    { step: 9,  action: 'click',     selector: 'text=Подробнее >> nth=0' },
    { step: 10, action: 'assert',    type: 'url',   expected: '/product/' },
    { step: 11, action: 'click',     selector: 'text=В корзину' },
    { step: 12, action: 'assert',    type: 'toast', expected: 'Добавлено в корзину' },
    { step: 13, action: 'click',     selector: 'text=Корзина' },
    { step: 14, action: 'assert',    type: 'url',   expected: '/cart' },
    { step: 15, action: 'assert',    type: 'element', selector: 'text=Ваша корзина', expected: 'visible' },
    { step: 16, action: 'assert',    type: 'element', selector: 'text=Оформить заказ', expected: 'visible' },
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

  /** Профиль пользователя */
  userProfileFlow: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/login' },
    { step: 2,  action: 'fill',      selector: '[data-testid="login-email"]',    value: '{{email}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="login-password"]', value: '{{password}}' },
    { step: 4,  action: 'click',     selector: '[data-testid="login-submit"]' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/profile' },
    { step: 6,  action: 'assert',    type: 'element', selector: 'text=Профиль', expected: 'visible' },
    { step: 7,  action: 'assert',    type: 'element', selector: 'text=Email', expected: 'visible' },
    { step: 8,  action: 'assert',    type: 'text', selector: 'body', expected: '{{email}}' },
  ],

  /** Заказы пользователя */
  userOrdersFlow: [
    { step: 1,  action: 'login',     persona: 'user' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/orders' },
    { step: 3,  action: 'assert',    type: 'element', selector: 'text=Мои заказы', expected: 'visible' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Заказ', expected: 'visible' },
  ],

  /** Отзывы */
  userReviewFlow: [
    { step: 1,  action: 'login',     persona: 'user' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 3,  action: 'click',     selector: 'text=Подробнее >> nth=0' },
    { step: 4,  action: 'assert',    type: 'url',   expected: '/product/' },
    { step: 5,  action: 'assert',    type: 'element', selector: 'text=Отзывы', expected: 'visible' },
  ],

  /** Корзина: изменение количества + удаление */
  cartManagementFlow: [
    { step: 1,  action: 'login',     persona: 'user' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 3,  action: 'click',     selector: 'text=Подробнее >> nth=0' },
    { step: 4,  action: 'click',     selector: 'text=В корзину' },
    { step: 5,  action: 'wait',      ms: 1000 },
    { step: 6,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/cart' },
    { step: 7,  action: 'assert',    type: 'element', selector: 'text=Ваша корзина', expected: 'visible' },
    { step: 8,  action: 'assert',    type: 'element', selector: 'text=Оформить заказ', expected: 'visible' },
  ],

  // ═══════════════════════════════════════════════════
  // ADMIN scenarios — Администратор
  // ═══════════════════════════════════════════════════

  /** Управление категориями */
  adminCategoryManagement: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/login' },
    { step: 2,  action: 'fill',      selector: '[data-testid="login-email"]',    value: '{{email}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="login-password"]', value: '{{password}}' },
    { step: 4,  action: 'click',     selector: '[data-testid="login-submit"]' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 6,  action: 'assert',    type: 'element', selector: 'text=Администрирование', expected: 'visible' },
    { step: 7,  action: 'click',     selector: 'text=Категории' },
    { step: 8,  action: 'click',     selector: 'text=Добавить категорию' },
    { step: 9,  action: 'fill',      selector: 'text=Название', value: 'Test Category {{random}}' },
    { step: 10, action: 'click',     selector: 'text=Сохранить' },
    { step: 11, action: 'assert',    type: 'text', selector: 'body', expected: 'Test Category' },
  ],

  /** Управление пользователями */
  adminUserManagement: [
    { step: 1,  action: 'login',     persona: 'admin' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 3,  action: 'click',     selector: 'text=Пользователи' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Пользователи', expected: 'visible' },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="user-row"]', expected: 'visible' },
  ],

  /** Управление заказами */
  adminOrderManagement: [
    { step: 1,  action: 'login',     persona: 'admin' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 3,  action: 'click',     selector: 'text=Заказы' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Заказы', expected: 'visible' },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="orders-table"]', expected: 'visible' },
  ],

  /** Статистика дашборда */
  adminDashboardStats: [
    { step: 1,  action: 'login',     persona: 'admin' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 3,  action: 'assert',    type: 'element', selector: 'text=Статистика', expected: 'visible' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Пользователи', expected: 'visible' },
    { step: 5,  action: 'assert',    type: 'element', selector: 'text=Заказы', expected: 'visible' },
    { step: 6,  action: 'assert',    type: 'element', selector: 'text=Выручка', expected: 'visible' },
  ],

  /** Управление способами доставки */
  adminDeliveryMethods: [
    { step: 1,  action: 'login',     persona: 'admin' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 3,  action: 'click',     selector: 'text=Способы доставки' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Способы доставки', expected: 'visible' },
    { step: 5,  action: 'assert',    type: 'element', selector: '[data-testid="delivery-methods-table"]', expected: 'visible' },
  ],

  // ═══════════════════════════════════════════════════
  // SUPPLIER scenarios — Поставщик
  // ═══════════════════════════════════════════════════

  /** Добавление товара */
  supplierAddProduct: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]',        value: '{{name}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]',       value: '{{email}}' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]',    value: '{{password}}' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: '{{password}}' },
    { step: 6,  action: 'click',     selector: '[data-testid="role-supplier"]' },
    { step: 7,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 8,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 9,  action: 'click',     selector: 'text=Добавить товар' },
    { step: 10, action: 'fill',      selector: 'text=Название',  value: 'Test Product {{random}}' },
    { step: 11, action: 'fill',      selector: 'text=Цена', value: '9999' },
    { step: 12, action: 'fill',      selector: 'text=Количество', value: '10' },
    { step: 13, action: 'click',     selector: 'text=Сохранить' },
    { step: 14, action: 'assert',    type: 'text', selector: 'body', expected: 'Test Product' },
  ],

  /** Редактирование товара */
  supplierEditProduct: [
    { step: 1,  action: 'login',     persona: 'supplier' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 3,  action: 'click',     selector: '[data-testid="edit-product-btn"]:first-child' },
    { step: 4,  action: 'fill',      selector: 'text=Название', value: 'Updated Product {{random}}' },
    { step: 5,  action: 'click',     selector: 'text=Сохранить' },
    { step: 6,  action: 'assert',    type: 'text', selector: 'body', expected: 'Updated Product' },
  ],

  /** Удаление товара */
  supplierDeleteProduct: [
    { step: 1,  action: 'login',     persona: 'supplier' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 3,  action: 'click',     selector: '[data-testid="delete-product-btn"]:first-child' },
    { step: 4,  action: 'assert',    type: 'toast', expected: 'удален' },
  ],

  /** Просмотр заказов поставщика */
  supplierOrdersFlow: [
    { step: 1,  action: 'login',     persona: 'supplier' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/supplier-orders' },
    { step: 3,  action: 'assert',    type: 'element', selector: 'text=Заказы', expected: 'visible' },
  ],

  // ═══════════════════════════════════════════════════
  // SECURITY scenarios — Безопасность
  // ═══════════════════════════════════════════════════

  /** Проверка доступов — гость не должен видеть защищённые страницы */
  unauthorizedAccess: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/cart' },
    { step: 2,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 3,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/admin' },
    { step: 4,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 6,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 7,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/orders' },
    { step: 8,  action: 'assert',    type: 'url', expected: '/login' },
    { step: 9,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/profile' },
    { step: 10, action: 'assert',    type: 'url', expected: '/login' },
  ],

  /** Валидация форм — пустые поля, невалидный email, короткий пароль */
  formValidation: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 3,  action: 'assert',    type: 'url', expected: '/register' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-email"]', value: 'invalid-email' },
    { step: 5,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 6,  action: 'assert',    type: 'url', expected: '/register' },
    { step: 7,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/login' },
    { step: 8,  action: 'fill',      selector: '[data-testid="login-email"]', value: 'nonexistent@test.com' },
    { step: 9,  action: 'fill',      selector: '[data-testid="login-password"]', value: 'wrong' },
    { step: 10, action: 'click',     selector: '[data-testid="login-submit"]' },
    { step: 11, action: 'assert',    type: 'url', expected: '/login' },
  ],

  /** SQL Injection / XSS базовые проверки */
  injectionChecks: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]', value: "<script>alert('xss')</script>" },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]', value: "test' OR '1'='1@test.com" },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]', value: 'TestPassword123!' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: 'TestPassword123!' },
    { step: 6,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 7,  action: 'assert',    type: 'url', expected: '/register' },
    { step: 8,  action: 'evaluate',  script: `() => { return document.querySelector('script')?.textContent?.includes("alert") || false; }` },
    { step: 9,  action: 'assert',    type: 'url', expected: '/register' },
  ],

  /** CSRF — проверка что API требует авторизацию */
  apiAuthorization: [
    { step: 1,  action: 'api',       method: 'GET',  path: '/me',         expected: { status: [401, 403] } },
    { step: 2,  action: 'api',       method: 'POST', path: '/cart/add',   expected: { status: [401, 403] }, body: { product_id: 1, quantity: 1 } },
    { step: 3,  action: 'api',       method: 'POST', path: '/orders/create', expected: { status: [401, 403] }, body: {} },
    { step: 4,  action: 'api',       method: 'POST', path: '/products/',  expected: { status: [401, 403] }, body: { name: 'test', price: 100 } },
    { step: 5,  action: 'api',       method: 'GET',  path: '/admin/users', expected: { status: [401, 403] } },
    { step: 6,  action: 'api',       method: 'GET',  path: '/admin/dashboard', expected: { status: [401, 403] } },
  ],

  // ═══════════════════════════════════════════════════
  // PERFORMANCE scenarios — Производительность
  // ═══════════════════════════════════════════════════

  /** Layout shift проверка — скролл должен быть стабильным */
  layoutStability: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'evaluate',  script: `() => { document.body.style.overflow = "hidden"; return "done"; }` },
    { step: 3,  action: 'screenshot', name: 'homepage-loaded' },
    { step: 4,  action: 'wait',      ms: 3000 },
    { step: 5,  action: 'screenshot', name: 'homepage-stable' },
    { step: 6,  action: 'evaluate',  script: `() => { const h = document.querySelector('header')?.getBoundingClientRect().height || 0; return h; }`, assert: { min: 40, max: 200 } },
  ],

  /** Core Web Vitals — LCP, CLS, FCP */
  coreWebVitals: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'wait',      ms: 2000 },
    { step: 3,  action: 'evaluate',  script: `() => {
      const nav = performance.getEntriesByType('navigation')[0];
      const lcp = performance.getEntriesByName('largest-contentful-paint')[0];
      const cls = performance.getEntriesByType('layout-shift')
        .filter(e => !e.hadRecentInput)
        .reduce((sum, e) => sum + e.value, 0);
      return {
        lcp: lcp?.startTime || 0,
        cls: cls,
        fcp: nav?.domContentLoadedEventEnd || 0,
        ttfb: nav?.responseStart || 0,
        loadTime: nav?.loadEventEnd || 0,
      };
    }`, assert: { lcp: { max: 4000 }, cls: { max: 0.1 }, fcp: { max: 2000 }, ttfb: { max: 1000 } } },
  ],

  /** API Response Time */
  apiPerformance: [
    { step: 1,  action: 'api',       method: 'GET',  path: '/products/?skip=0&limit=20', expected: { status: 200, duration: { max: 1000 } } },
    { step: 2,  action: 'api',       method: 'GET',  path: '/categories/',               expected: { status: 200, duration: { max: 500 } } },
    { step: 3,  action: 'api',       method: 'GET',  path: '/health',                    expected: { status: 200, duration: { max: 200 } } },
  ],

  // ═══════════════════════════════════════════════════
  // CROSS-ROLE scenarios — Сквозные сценарии
  // ═══════════════════════════════════════════════════

  /** Админ создаёт категорию → Поставщик добавляет товар → Пользователь покупает */
  endToEndPurchase: [
    { step: 1,  action: 'api',       method: 'POST', path: '/login', as: 'admin', storeToken: 'admin', body: { email: '{{admin_email}}', password: '{{admin_password}}' } },
    { step: 2,  action: 'api',       method: 'POST', path: '/categories/', as: 'admin', storeResult: 'category', body: { name: 'E2E Category {{random}}', description: 'Test' } },
    { step: 3,  action: 'api',       method: 'POST', path: '/register', storeResult: 'supplier', body: { name: 'E2E Supplier {{random}}', email: '{{supplier_email}}', password: '{{password}}', role: 'supplier', password_confirm: '{{password}}' } },
    { step: 4,  action: 'api',       method: 'POST', path: '/login', as: 'supplier', storeToken: 'supplier', body: { email: '{{supplier_email}}', password: '{{password}}' } },
    { step: 5,  action: 'api',       method: 'POST', path: '/products/', as: 'supplier', storeResult: 'product', body: { name: 'E2E Product {{random}}', price: 999, stock: 10, category_id: '{{category_id}}' } },
    { step: 6,  action: 'api',       method: 'POST', path: '/register', storeResult: 'user', body: { name: 'E2E User {{random}}', email: '{{user_email}}', password: '{{password}}', role: 'user', password_confirm: '{{password}}' } },
    { step: 7,  action: 'api',       method: 'POST', path: '/login', as: 'user', storeToken: 'user', body: { email: '{{user_email}}', password: '{{password}}' } },
    { step: 8,  action: 'api',       method: 'POST', path: '/cart/add', as: 'user', body: { product_id: '{{product_id}}', quantity: 1 } },
    { step: 9,  action: 'api',       method: 'GET',  path: '/cart/', as: 'user', expected: { arrayMinLength: 1 } },
    { step: 10, action: 'api',       method: 'DELETE', path: '/products/{{product_id}}', as: 'supplier' },
    { step: 11, action: 'api',       method: 'DELETE', path: '/categories/{{category_id}}', as: 'admin' },
  ],

  // ═══════════════════════════════════════════════════
  // FUZZ scenarios — Случайные данные
  // ═══════════════════════════════════════════════════

  /** Регистрация с edge case данными */
  fuzzRegistration: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/register' },
    { step: 2,  action: 'fill',      selector: '[data-testid="register-name"]', value: '{{fuzz_string_50}}' },
    { step: 3,  action: 'fill',      selector: '[data-testid="register-email"]', value: '{{fuzz_email}}' },
    { step: 4,  action: 'fill',      selector: '[data-testid="register-password"]', value: '{{fuzz_password}}' },
    { step: 5,  action: 'fill',      selector: '[data-testid="register-password-confirm"]', value: '{{fuzz_password}}' },
    { step: 6,  action: 'click',     selector: '[data-testid="register-submit"]' },
    { step: 7,  action: 'assert',    type: 'text', selector: 'body', expected: 'обязательно' },
  ],

  /** Добавление товара с extreme ценами */
  fuzzProductCreation: [
    { step: 1,  action: 'login',     persona: 'supplier' },
    { step: 2,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/my-products' },
    { step: 3,  action: 'click',     selector: 'text=Добавить товар' },
    { step: 4,  action: 'fill',      selector: 'text=Название', value: '{{fuzz_string_100}}' },
    { step: 5,  action: 'fill',      selector: 'text=Цена', value: '{{fuzz_price}}' },
    { step: 6,  action: 'fill',      selector: 'text=Количество', value: '{{fuzz_stock}}' },
    { step: 7,  action: 'click',     selector: 'text=Сохранить' },
    { step: 8,  action: 'assert',    type: 'url', expected: '/my-products' },
  ],

  // ═══════════════════════════════════════════════════
  // ACCESSIBILITY scenarios
  // ═══════════════════════════════════════════════════

  /** A11y: наличие alt у изображений, aria-labels, заголовки */
  accessibilityCheck: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'evaluate',  script: `() => {
      const images = Array.from(document.querySelectorAll('img'));
      const withoutAlt = images.filter(img => !img.alt).length;
      const headings = Array.from(document.querySelectorAll('h1, h2, h3'));
      const ariaLabels = Array.from(document.querySelectorAll('[aria-label]')).length;
      const focusable = Array.from(document.querySelectorAll('button, a, input, select, textarea'));
      const withoutFocus = focusable.filter(el => el.tabIndex < 0 && !el.disabled).length;
      return { totalImages: images.length, withoutAlt, headings: headings.length, ariaLabels, focusable: focusable.length, withoutFocus };
    }`, assert: { withoutAlt: { max: 5 }, headings: { min: 1 } } },
  ],

  // ═══════════════════════════════════════════════════
  // RESPONSIVE scenarios
  // ═══════════════════════════════════════════════════

  /** Мобильный viewport */
  responsiveMobile: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'evaluate',  script: `() => { window.innerWidth = 375; window.innerHeight = 812; return "done"; }` },
    { step: 3,  action: 'screenshot', name: 'mobile-homepage' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Популярные товары', expected: 'visible' },
    { step: 5,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/login' },
    { step: 6,  action: 'screenshot', name: 'mobile-login' },
    { step: 7,  action: 'assert',    type: 'element', selector: 'text=Вход', expected: 'visible' },
  ],

  /** Планшетный viewport */
  responsiveTablet: [
    { step: 1,  action: 'navigate',  target: 'https://promelectron-test.aidrivencode.ru/' },
    { step: 2,  action: 'evaluate',  script: `() => { window.innerWidth = 768; window.innerHeight = 1024; return "done"; }` },
    { step: 3,  action: 'screenshot', name: 'tablet-homepage' },
    { step: 4,  action: 'assert',    type: 'element', selector: 'text=Популярные товары', expected: 'visible' },
  ],
};

/**
 * Получить сценарии для конкретной роли или категории
 */
export function getScenariosForPersona(personaKey) {
  const map = {
    user: [
      'fullPurchaseFlow',
      'searchAndFilter',
      'favoritesFlow',
      'userProfileFlow',
      'userOrdersFlow',
      'userReviewFlow',
      'cartManagementFlow',
      'unauthorizedAccess',
      'layoutStability',
      'coreWebVitals',
      'accessibilityCheck',
      'responsiveMobile',
      'responsiveTablet',
    ],
    admin: [
      'adminCategoryManagement',
      'adminUserManagement',
      'adminOrderManagement',
      'adminDashboardStats',
      'adminDeliveryMethods',
      'unauthorizedAccess',
      'layoutStability',
      'apiAuthorization',
    ],
    supplier: [
      'supplierAddProduct',
      'supplierEditProduct',
      'supplierDeleteProduct',
      'supplierOrdersFlow',
      'unauthorizedAccess',
      'layoutStability',
    ],
    security: [
      'unauthorizedAccess',
      'formValidation',
      'injectionChecks',
      'apiAuthorization',
    ],
    performance: [
      'layoutStability',
      'coreWebVitals',
      'apiPerformance',
    ],
    crossrole: [
      'endToEndPurchase',
    ],
    fuzz: [
      'fuzzRegistration',
      'fuzzProductCreation',
    ],
    accessibility: [
      'accessibilityCheck',
    ],
    responsive: [
      'responsiveMobile',
      'responsiveTablet',
    ],
    all: Object.keys(scenarios),
  };
  const keys = map[personaKey] || map.all;
  return keys.map((k) => ({ name: k, steps: scenarios[k] }));
}
