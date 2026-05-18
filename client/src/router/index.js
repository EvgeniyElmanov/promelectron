import { createRouter, createWebHistory } from 'vue-router';
import { jwtDecode } from 'jwt-decode';
import { useAuth } from '@/composables/useAuth';
import Products from '../views/Products.vue';
import Login from '../views/Login.vue';
import Cart from '../views/Cart.vue';
import Orders from '../views/Orders.vue';
import Profile from '../views/Profile.vue';
import ProfileEdit from '../views/ProfileEdit.vue';
import Register from '../views/Register.vue';
import AuthCallback from '../views/AuthCallback.vue';
import ProductDetail from '../views/ProductDetail.vue';
import Favorites from '../views/Favorites.vue';
import SupplierProducts from '../views/SupplierProducts.vue';
import Admin from '../views/Admin.vue';
import OrderDetail from '../views/OrderDetail.vue';

const routes = [
  { path: '/', component: Products },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/admin', component: Admin },
  { path: '/cart', component: Cart, meta: { requiresAuth: true } },
  { path: '/orders', component: Orders, meta: { requiresAuth: true } },
  { path: '/orders/:id', component: OrderDetail, meta: { requiresAuth: true } },
  { path: '/profile', component: Profile, meta: { requiresAuth: true } },
  { path: '/profile/edit', component: ProfileEdit, meta: { requiresAuth: true } },
  { path: '/auth/callback', component: AuthCallback },
  { path: '/product/:id', component: ProductDetail },
  { path: '/favorites', component: Favorites, meta: { requiresAuth: true } },
  { path: '/my-products', component: SupplierProducts, meta: { requiresAuth: true, requiresSupplier: true } },
  { path: '/admin', component: Admin, meta: { requiresAuth: true, requiresAdmin: true } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token');
  const { getUserRole } = useAuth();

  if (to.meta.requiresAuth) {
    if (!token) {
      next('/login');
      return;
    }
    // Проверяем, не протух ли токен
    try {
      const decoded = jwtDecode(token);
      if (decoded.exp && decoded.exp * 1000 < Date.now()) {
        localStorage.removeItem('access_token');
        next('/login');
        return;
      }
    } catch {
      localStorage.removeItem('access_token');
      next('/login');
      return;
    }
  }

  if (to.meta.requiresSupplier && getUserRole() !== 'supplier') {
    next('/');
    return;
  }

  if (to.meta.requiresAdmin && getUserRole() !== 'admin') {
    next('/');
    return;
  }

  next();
});

export default router;
