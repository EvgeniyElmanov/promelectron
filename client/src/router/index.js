import { createRouter, createWebHistory } from 'vue-router';
import Products from '../views/Products.vue';
import Login from '../views/Login.vue';
import Admin from '../views/Admin.vue';
import Cart from '../views/Cart.vue';
import Orders from '../views/Orders.vue';
import Profile from '../views/Profile.vue';
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
  if (to.meta.requiresAuth && !token) {
    next('/login');
  } else {
    next();
  }
});

export default router;
