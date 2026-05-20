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
    ],
    shouldSee: [
      'admin-dashboard',
      'categories-table',
      'users-table',
      'orders-table',
      'stats-cards',
      'delivery-methods-table',
    ],
    shouldNotSee: ['supplier-products', 'register-page'],
    dataTestIds: {
      loginBtn: '[data-testid="login-submit"]',
      adminNav: '[data-testid="admin-nav"]',
      categoriesTab: '[data-testid="categories-tab"]',
      usersTab: '[data-testid="users-tab"]',
      ordersTab: '[data-testid="orders-tab"]',
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
    ],
    shouldSee: [
      'supplier-dashboard',
      'my-products-list',
      'product-form',
      'add-product-btn',
      'order-list',
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
    },
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
