/**
 * Persona System — роли для автономного тестера
 * Каждая роль знает что может делать и что должна видеть
 */

export const personas = {
  user: {
    key: 'user',
    name: 'Обычный покупатель',
    emailPrefix: 'buyer',
    can: [
      'register',
      'login',
      'browse_catalog',
      'search_products',
      'filter_by_category',
      'sort_products',
      'view_product_detail',
      'add_to_cart',
      'add_to_favorites',
      'add_review',
      'view_cart',
      'update_cart_quantity',
      'remove_from_cart',
      'checkout',
      'view_orders',
      'cancel_order',
      'view_profile',
      'edit_profile',
      'change_password',
    ],
    shouldSee: [
      'search-bar',
      'category-chips',
      'product-card',
      'cart-link',
      'profile-link',
      'bottom-nav',
      'product-count',
    ],
    shouldNotSee: ['admin-panel', 'supplier-dashboard', 'user-block-btn'],
    dataTestIds: {
      registerBtn: '[data-testid="register-submit"]',
      loginBtn: '[data-testid="login-submit"]',
      addToCart: '[data-testid="add-to-cart-button"]',
      favoriteBtn: '[data-testid="favorite-button"]',
      cartLink: '[data-testid="cart-link"]',
      profileLink: '[data-testid="profile-link"]',
      searchBar: '[data-testid="search-bar"]',
      sortSelect: '[data-testid="sort-select"]',
      checkoutBtn: '[data-testid="checkout-button"]',
    },
  },

  admin: {
    key: 'admin',
    name: 'Администратор',
    emailPrefix: 'admin',
    defaultCredentials: {
      email: 'admin@myshop.ru',
      password: 'admin123',
    },
    can: [
      'login',
      'view_admin_dashboard',
      'manage_categories',
      'manage_delivery_methods',
      'manage_users',
      'block_user',
      'view_all_orders',
      'edit_order_status',
      'view_stats',
      'view_top_products',
      'view_orders_by_day',
    ],
    shouldSee: [
      'admin-dashboard',
      'categories-table',
      'users-table',
      'orders-table',
      'stats-cards',
      'delivery-methods-table',
      'top-products-chart',
      'orders-by-day-chart',
    ],
    shouldNotSee: ['supplier-products', 'register-page'],
    dataTestIds: {
      loginBtn: '[data-testid="login-submit"]',
      adminNav: '[data-testid="admin-nav"]',
      categoriesTab: '[data-testid="categories-tab"]',
      usersTab: '[data-testid="users-tab"]',
      ordersTab: '[data-testid="orders-tab"]',
      statsTab: '[data-testid="stats-tab"]',
      deliveryTab: '[data-testid="delivery-tab"]',
      addCategoryBtn: '[data-testid="add-category-btn"]',
      saveCategoryBtn: '[data-testid="save-category-btn"]',
      blockUserBtn: '[data-testid="block-user-btn"]',
    },
  },

  supplier: {
    key: 'supplier',
    name: 'Поставщик',
    emailPrefix: 'supplier',
    can: [
      'register_as_supplier',
      'login',
      'view_my_products',
      'add_product',
      'edit_product',
      'delete_product',
      'upload_product_image',
      'view_orders_as_supplier',
      'update_order_status',
    ],
    shouldSee: [
      'supplier-dashboard',
      'my-products-list',
      'product-form',
      'add-product-btn',
      'order-list',
      'supplier-stats',
    ],
    shouldNotSee: ['admin-panel', 'register-page-when-logged'],
    dataTestIds: {
      registerBtn: '[data-testid="register-submit"]',
      loginBtn: '[data-testid="login-submit"]',
      myProductsLink: '[data-testid="my-products-link"]',
      addProductBtn: '[data-testid="add-product-btn"]',
      productName: '[data-testid="product-name-input"]',
      productPrice: '[data-testid="product-price-input"]',
      productStock: '[data-testid="product-stock-input"]',
      saveProductBtn: '[data-testid="save-product-btn"]',
      deleteProductBtn: '[data-testid="delete-product-btn"]',
      editProductBtn: '[data-testid="edit-product-btn"]',
      supplierOrdersLink: '[data-testid="supplier-orders-link"]',
    },
  },

  security: {
    key: 'security',
    name: 'Security Auditor',
    emailPrefix: 'security',
    can: [
      'test_unauthorized_access',
      'test_form_validation',
      'test_sql_injection',
      'test_xss',
      'test_csrf',
      'test_api_authorization',
      'test_rate_limiting',
    ],
    shouldSee: ['login-form', 'register-form'],
    shouldNotSee: ['admin-panel', 'supplier-dashboard'],
  },

  performance: {
    key: 'performance',
    name: 'Performance Engineer',
    emailPrefix: 'perf',
    can: [
      'measure_lcp',
      'measure_cls',
      'measure_fcp',
      'measure_ttfb',
      'measure_api_response_time',
      'measure_layout_stability',
    ],
    shouldSee: [],
    shouldNotSee: [],
  },
};

/**
 * Генератор уникальных кредов для регистрации
 */
export function generateCredentials(persona) {
  const ts = Date.now();
  const prefix = persona.emailPrefix || 'user';
  return {
    email: `${prefix}_${ts}@test.com`,
    password: 'TestPassword123!',
    name: `${persona.name} ${ts}`,
  };
}

/**
 * Генератор fuzz данных
 */
export function generateFuzzData() {
  const randomString = (len) => {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-%$#@!*()[]{}';
    return Array.from({ length: len }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  };

  return {
    fuzz_string_50: randomString(50),
    fuzz_string_100: randomString(100),
    fuzz_string_255: randomString(255),
    fuzz_email: `fuzz_${Date.now()}@test.com`,
    fuzz_password: `Pass${randomString(10)}!`,
    fuzz_price: Math.floor(Math.random() * 1000000).toString(),
    fuzz_stock: Math.floor(Math.random() * 10000).toString(),
    fuzz_negative: (-Math.floor(Math.random() * 1000)).toString(),
    fuzz_zero: '0',
    fuzz_special: "<script>alert('xss')</script>",
    fuzz_sql: "' OR '1'='1",
    fuzz_unicode: '测试用户🚀日本語مرحبا',
    fuzz_html: '<b>Bold</b><i>Italic</i>',
  };
}

/**
 * Cross-role credentials для end-to-end сценариев
 */
export function generateCrossRoleCredentials() {
  const ts = Date.now();
  return {
    admin_email: 'admin@myshop.ru',
    admin_password: 'admin123',
    supplier_email: `supplier_e2e_${ts}@test.com`,
    user_email: `user_e2e_${ts}@test.com`,
    password: 'TestPassword123!',
    random: ts.toString(),
  };
}
