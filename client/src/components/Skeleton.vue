<template>
  <div
    class="skeleton"
    :class="{ 'skeleton--circle': circle, [`skeleton--${size}`]: size }"
    :style="inlineStyle"
  />
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  width: { type: String, default: null },
  height: { type: String, default: null },
  circle: { type: Boolean, default: false },
  size: { type: String, default: null },
});

const inlineStyle = computed(() => {
  const s = {};
  if (props.width) s.width = props.width;
  if (props.height) s.height = props.height;
  return s;
});
</script>

<style scoped>
.skeleton {
  background: linear-gradient(
    90deg,
    var(--color-bg) 25%,
    #e8ecf1 50%,
    var(--color-bg) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8px;
}

.skeleton--circle {
  border-radius: 50%;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
