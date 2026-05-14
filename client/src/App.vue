<template>
  <div class="desktop-container">
    <Header />
    <RouterView />
    <BottomNav />
  </div>
</template>

<script setup>
import Header from '@/components/Header.vue';
import BottomNav from '@/components/BottomNav.vue';
</script>
