<template>
  <div class="desktop-container">
    <Header />
    <CategoryNav />
    <RouterView />
    <BottomNav />
  </div>
</template>

<script setup>
import Header from '@/components/Header.vue';
import CategoryNav from '@/components/CategoryNav.vue';
import BottomNav from '@/components/BottomNav.vue';
</script>
