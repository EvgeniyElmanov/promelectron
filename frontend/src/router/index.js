import { createRouter, createWebHistory } from 'vue-router';
import Products from '../views/Products.vue';
import Login from '../views/Login.vue';
import Admin from '../views/Admin.vue';
import Cart from '../views/Cart.vue';
import Orders from '../views/Orders.vue';
import Profile from '../views/Profile.vue';

const routes = [
  { path: '/', component: Products },
  { path: '/login', component: Login },
  { path: '/admin', component: Admin },
  { path: '/cart', component: Cart },
  { path: '/orders', component: Orders },
  { path: '/profile', component: Profile },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
