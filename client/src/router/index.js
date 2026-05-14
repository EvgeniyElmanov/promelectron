import { createRouter, createWebHistory } from 'vue-router';
import { jwtDecode } from 'jwt-decode';
import Products from '../views/Products.vue';
import Login from '../views/Login.vue';
import Admin from '../views/Admin.vue';
import Cart from '../views/Cart.vue';
import Orders from '../views/Orders.vue';
import Profile from '../views/Profile.vue';
import ProfileEdit from '../views/ProfileEdit.vue';
import Register from '../views/Register.vue';
import AuthCallback from '../views/AuthCallback.vue';
import ProductDetail from '../views/ProductDetail.vue';
import Favorites from '../views/Favorites.vue';

const routes = [
  { path: '/', component: Products },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/admin', component: Admin },
  { path: '/cart', component: Cart, meta: { requiresAuth: true } },
  { path: '/orders', component: Orders, meta: { requiresAuth: true } },
  { path: '/profile', component: Profile, meta: { requiresAuth: true } },
  { path: '/profile/edit', component: ProfileEdit, meta: { requiresAuth: true } },
  { path: '/auth/callback', component: AuthCallback },
  { path: '/product/:id', component: ProductDetail },
  { path: '/favorites', component: Favorites, meta: { requiresAuth: true } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token');

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

  next();
});

export default router;
