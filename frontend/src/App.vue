<template>
  <div class="desktop-container">
    <Header />
    <CategoryNav />
    <RouterView />
    <BottomNav />
  </div>
</template>

<script setup>
import { watchEffect } from 'vue';
import { useRoute } from 'vue-router';
import Header from '@/components/Header.vue';
import CategoryNav from '@/components/CategoryNav.vue';
import BottomNav from '@/components/BottomNav.vue';

const route = useRoute();

watchEffect(() => {
  document.body.classList.toggle('has-bottom-nav', route.path !== '/');
});
</script>
