/**
 * API Testing Layer — полное покрытие backend API
 * Проверяет API независимо от UI для нахождения серверных багов
 */

const BASE_API = (process.env.TEST_API_URL || 'https://api.promelectron-test.aidrivencode.ru').replace(/\/$/, '') + '/api/v1';

export class ApiClient {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || BASE_API;
    this.tokens = {};
    this.debug = options.debug || false;
    this.requestLog = [];
  }

  setToken(role, token) {
    this.tokens[role] = token;
  }

  getToken(role) {
    return this.tokens[role];
  }

  async request(method, path, options = {}) {
    const url = path.startsWith('http') ? path : `${this.baseUrl}${path}`;
    const headers = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    };

    const role = options.as || 'anonymous';
    const token = this.tokens[role];
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const body = options.body ? JSON.stringify(options.body) : undefined;

    const startTime = Date.now();
    let response;
    let responseText;

    try {
      response = await fetch(url, { method, headers, body });
      responseText = await response.text();
    } catch (e) {
      this.logRequest({ method, url, role, error: e.message, duration: Date.now() - startTime });
      return { ok: false, error: e.message, status: 0 };
    }

    let data;
    try {
      data = JSON.parse(responseText);
    } catch {
      data = responseText;
    }

    const result = {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      headers: Object.fromEntries(response.headers.entries()),
      data,
      duration: Date.now() - startTime,
    };

    this.logRequest({ method, url, role, status: response.status, duration: result.duration });
    return result;
  }

  logRequest(entry) {
    this.requestLog.push({ ...entry, time: new Date().toISOString() });
    if (this.debug) {
      const status = entry.error ? `ERROR ${entry.error}` : entry.status;
      console.log(`[API] ${entry.method} ${entry.url} → ${status} (${entry.duration}ms)`);
    }
  }

  // ═══════════════════════════════════════
  // Auth API
  // ═══════════════════════════════════════

  async register(credentials) {
    return this.request('POST', '/register', { body: credentials });
  }

  async login(credentials) {
    const result = await this.request('POST', '/login', { body: credentials });
    if (result.ok && result.data?.access_token) {
      const role = credentials.role || 'user';
      this.setToken(role, result.data.access_token);
    }
    return result;
  }

  async socialLogin(provider) {
    return this.request('GET', `/auth/${provider}/login`);
  }

  async socialCallback(provider, code) {
    return this.request('GET', `/auth/${provider}/callback?code=${code}`);
  }

  // ═══════════════════════════════════════
  // Users API
  // ═══════════════════════════════════════

  async getMe(role = 'user') {
    // /me works for all roles (user, admin, supplier)
    return this.request('GET', '/me', { as: role });
  }

  async updateMe(updates, role = 'user') {
    return this.request('PATCH', '/me', { body: updates, as: role });
  }

  async updatePassword(passwordData, role = 'user') {
    return this.request('PATCH', '/me/password', { body: passwordData, as: role });
  }

  async uploadAvatar(fileData, role = 'user') {
    return this.request('POST', '/me/avatar/', { body: fileData, as: role, headers: { 'Content-Type': 'multipart/form-data' } });
  }

  async getProfile(role = 'user') {
    return this.request('GET', '/profile', { as: role });
  }

  // ═══════════════════════════════════════
  // Products API
  // ═══════════════════════════════════════

  async getProducts(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request('GET', `/products/${qs ? '?' + qs : ''}`);
  }

  async getProduct(id) {
    return this.request('GET', `/products/${id}`);
  }

  async getProductDetail(id) {
    return this.request('GET', `/products/${id}/detail`);
  }

  async createProduct(product, role = 'supplier') {
    return this.request('POST', '/products/', { body: product, as: role });
  }

  async updateProduct(id, product, role = 'supplier') {
    return this.request('PUT', `/products/${id}`, { body: product, as: role });
  }

  async deleteProduct(id, role = 'supplier') {
    return this.request('DELETE', `/products/${id}`, { as: role });
  }

  async uploadProductImage(productId, imageData, role = 'supplier') {
    return this.request('POST', `/products/${productId}/images`, { body: imageData, as: role, headers: { 'Content-Type': 'multipart/form-data' } });
  }

  async deleteProductImage(productId, filename, role = 'supplier') {
    return this.request('DELETE', `/products/${productId}/images/${filename}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Categories API
  // ═══════════════════════════════════════

  async getCategories() {
    return this.request('GET', '/categories/');
  }

  async getCategory(id) {
    return this.request('GET', `/categories/${id}`);
  }

  async createCategory(category, role = 'admin') {
    return this.request('POST', '/categories/', { body: category, as: role });
  }

  async updateCategory(id, category, role = 'admin') {
    return this.request('PUT', `/categories/${id}`, { body: category, as: role });
  }

  async deleteCategory(id, role = 'admin') {
    return this.request('DELETE', `/categories/${id}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Cart API
  // ═══════════════════════════════════════

  async getCart(role = 'user') {
    return this.request('GET', '/cart/', { as: role });
  }

  async addToCart(productId, quantity = 1, role = 'user') {
    return this.request('POST', '/cart/add', { body: { product_id: productId, quantity }, as: role });
  }

  async updateCartItem(itemId, quantity, role = 'user') {
    return this.request('PUT', `/cart/update/${itemId}`, { body: { quantity }, as: role });
  }

  async removeFromCart(itemId, role = 'user') {
    return this.request('DELETE', `/cart/remove/${itemId}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Orders API
  // ═══════════════════════════════════════

  async getOrders(role = 'user') {
    return this.request('GET', '/orders/', { as: role });
  }

  async getOrder(id, role = 'user') {
    return this.request('GET', `/orders/${id}`, { as: role });
  }

  async createOrder(order, role = 'user') {
    return this.request('POST', '/orders/', { body: order, as: role });
  }

  async cancelOrder(id, role = 'user') {
    return this.request('PATCH', `/orders/${id}/cancel`, { as: role });
  }

  async updateOrderStatus(id, status, role = 'admin') {
    return this.request('PUT', `/orders/${id}/status`, { body: { status }, as: role });
  }

  // ═══════════════════════════════════════
  // Favorites API
  // ═══════════════════════════════════════

  async getFavorites(role = 'user') {
    return this.request('GET', '/favorites/', { as: role });
  }

  async addFavorite(productId, role = 'user') {
    return this.request('POST', `/favorites/add/${productId}`, { as: role });
  }

  async removeFavorite(productId, role = 'user') {
    return this.request('DELETE', `/favorites/remove/${productId}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Reviews API
  // ═══════════════════════════════════════

  async getReviews(productId) {
    return this.request('GET', `/reviews/product/${productId}`);
  }

  async createReview(productId, review, role = 'user') {
    return this.request('POST', `/reviews/product/${productId}`, { body: review, as: role });
  }

  async updateReview(id, review, role = 'user') {
    return this.request('PUT', `/reviews/${id}`, { body: review, as: role });
  }

  async deleteReview(id, role = 'user') {
    return this.request('DELETE', `/reviews/${id}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Payments API
  // ═══════════════════════════════════════

  async getPayment(id, role = 'user') {
    return this.request('GET', `/payments/${id}`, { as: role });
  }

  async createPayment(payment, role = 'user') {
    return this.request('POST', '/payments/create', { body: payment, as: role });
  }

  async confirmPayment(id, role = 'user') {
    return this.request('POST', `/payments/${id}/confirm`, { as: role });
  }

  async cancelPayment(id, role = 'user') {
    return this.request('POST', `/payments/${id}/cancel`, { as: role });
  }

  // ═══════════════════════════════════════
  // Notifications API
  // ═══════════════════════════════════════

  async getNotifications(role = 'user') {
    return this.request('GET', '/notifications/', { as: role });
  }

  async getUnreadCount(role = 'user') {
    return this.request('GET', '/notifications/unread-count', { as: role });
  }

  async markNotificationRead(id, role = 'user') {
    return this.request('PATCH', `/notifications/${id}/read`, { as: role });
  }

  async markAllNotificationsRead(role = 'user') {
    return this.request('PATCH', '/notifications/read-all', { as: role });
  }

  async deleteNotification(id, role = 'user') {
    return this.request('DELETE', `/notifications/${id}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Delivery Methods API
  // ═══════════════════════════════════════

  async getDeliveryMethods() {
    return this.request('GET', '/delivery-methods/');
  }

  async getDeliveryMethod(id) {
    return this.request('GET', `/delivery-methods/${id}`);
  }

  async createDeliveryMethod(method, role = 'admin') {
    return this.request('POST', '/delivery-methods/', { body: method, as: role });
  }

  async updateDeliveryMethod(id, method, role = 'admin') {
    return this.request('PUT', `/delivery-methods/${id}`, { body: method, as: role });
  }

  async deleteDeliveryMethod(id, role = 'admin') {
    return this.request('DELETE', `/delivery-methods/${id}`, { as: role });
  }

  // ═══════════════════════════════════════
  // Admin API
  // ═══════════════════════════════════════

  async getAdminStats(role = 'admin') {
    return this.request('GET', '/admin/dashboard', { as: role });
  }

  async getAdminDashboard(role = 'admin') {
    return this.request('GET', '/admin/dashboard', { as: role });
  }

  async getAdminUsers(role = 'admin') {
    return this.request('GET', '/admin/users', { as: role });
  }

  async toggleUserActive(userId, role = 'admin') {
    return this.request('PATCH', `/admin/users/${userId}/toggle-active`, { as: role });
  }

  async getAdminOrders(role = 'admin') {
    return this.request('GET', '/admin/orders', { as: role });
  }

  async updateAdminOrder(orderId, updates, role = 'admin') {
    return this.request('PUT', `/admin/orders/${orderId}`, { body: updates, as: role });
  }

  async getAdminOrdersByDay(role = 'admin') {
    return this.request('GET', '/admin/orders-by-day', { as: role });
  }

  async getAdminTopProducts(role = 'admin') {
    return this.request('GET', '/admin/top-products', { as: role });
  }

  // ═══════════════════════════════════════
  // Supplier API
  // ═══════════════════════════════════════

  async getSupplierProducts(role = 'supplier') {
    return this.request('GET', '/products/my', { as: role });
  }

  async getSupplierOrders(role = 'supplier') {
    // No dedicated supplier orders endpoint; reuse general orders endpoint
    return this.request('GET', '/orders/', { as: role });
  }

  // ═══════════════════════════════════════
  // Health & probes
  // ═══════════════════════════════════════

  async health() {
    // Backend health is at /health without /api/v1 prefix
    const baseUrl = this.baseUrl.replace(/\/api\/v1\/?$/, '');
    const url = baseUrl + '/health';
    const startTime = Date.now();
    let response;
    let responseText;
    try {
      response = await fetch(url, {
        headers: { 'Accept': 'application/json', 'User-Agent': 'promelectron-e2e/1.0' },
      });
      responseText = await response.text();
    } catch (e) {
      return { ok: false, error: e.message, status: 0, name: 'health' };
    }
    let data;
    try { data = JSON.parse(responseText); } catch { data = responseText; }
    return {
      ok: response.ok,
      status: response.status,
      statusText: response.statusText,
      data,
      duration: Date.now() - startTime,
      name: 'health',
    };
  }

  async root() {
    return this.request('GET', '/');
  }

  // ═══════════════════════════════════════
  // Validation helpers
  // ═══════════════════════════════════════

  validateResponse(result, expected) {
    const issues = [];

    if (expected.status && result.status !== expected.status) {
      issues.push(`Expected status ${expected.status}, got ${result.status}`);
    }

    if (expected.ok !== undefined && result.ok !== expected.ok) {
      issues.push(`Expected ok=${expected.ok}, got ${result.ok}`);
    }

    if (expected.hasField) {
      const field = expected.hasField;
      if (!result.data || result.data[field] === undefined) {
        issues.push(`Missing field "${field}" in response`);
      }
    }

    if (expected.arrayMinLength !== undefined) {
      const arr = Array.isArray(result.data) ? result.data : result.data?.items || result.data?.results;
      if (!arr || arr.length < expected.arrayMinLength) {
        issues.push(`Expected array length >= ${expected.arrayMinLength}, got ${arr?.length || 0}`);
      }
    }

    if (expected.duration?.max && result.duration > expected.duration.max) {
      issues.push(`Duration ${result.duration}ms > max ${expected.duration.max}ms`);
    }

    return { valid: issues.length === 0, issues };
  }
}
