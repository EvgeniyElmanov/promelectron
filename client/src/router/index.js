import { createRouter, createWebHistory } from 'vue-router';
import Products from '../views/Products.vue';
import Login from '../views/Login.vue';
import Admin from '../views/Admin.vue';
import Cart from '../views/Cart.vue';
import Orders from '../views/Orders.vue';
import Profile from '../views/Profile.vue';
import Register from '../views/Register.vue';
import AuthCallback from '../views/AuthCallback.vue';

const routes = [
  { path: '/', component: Products },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/admin', component: Admin },
  { path: '/cart', component: Cart },
  { path: '/orders', component: Orders },
  { path: '/profile', component: Profile },
  { path: '/auth/callback', component: AuthCallback },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
