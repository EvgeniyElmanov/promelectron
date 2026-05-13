<template>
  <div class="promo-banner">
    <div class="promo-banner__track">
      <div
        v-for="(banner, i) in banners"
        :key="i"
        class="promo-banner__card"
        :style="{ background: banner.bg }"
      >
        <div class="promo-banner__text">
          <div class="promo-banner__title">{{ banner.title }}</div>
          <div class="promo-banner__subtitle">{{ banner.subtitle }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const banners = [
  {
    title: 'Скидки до -30%',
    subtitle: 'На популярные товары',
    bg: 'linear-gradient(135deg, #667eea, #764ba2)',
  },
  {
    title: 'Новинки',
    subtitle: 'Только поступили в продажу',
    bg: 'linear-gradient(135deg, #f093fb, #f5576c)',
  },
  {
    title: 'Бесплатная доставка',
    subtitle: 'При заказе от 3000 ₽',
    bg: 'linear-gradient(135deg, #4facfe, #00f2fe)',
  },
];
</script>

<style scoped>
.promo-banner {
  padding: 8px 12px;
  background: var(--color-bg-white);
}

.promo-banner__track {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.promo-banner__track::-webkit-scrollbar {
  display: none;
}

.promo-banner__card {
  flex: 0 0 85%;
  scroll-snap-align: start;
  border-radius: 12px;
  padding: 20px 16px;
  color: #fff;
  min-height: 100px;
  display: flex;
  align-items: center;
}

.promo-banner__title {
  font-size: 18px;
  font-weight: 700;
}

.promo-banner__subtitle {
  font-size: 13px;
  opacity: 0.9;
  margin-top: 4px;
}
</style>