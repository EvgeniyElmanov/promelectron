<template>
  <div class="desktop-container">
    <Header />
    <RouterView />
    <BottomNav />
    <ToastContainer />
  </div>
</template>

<script setup>
import Header from '@/components/Header.vue';
import BottomNav from '@/components/BottomNav.vue';
import ToastContainer from '@/components/ToastContainer.vue';
</script>
