<template>
  <div class="cdek-widget" data-testid="cdek-delivery-widget">
    <h3 class="cdek-widget__title">Доставка СДЭК</h3>

    <div v-if="!selectedDelivery" class="cdek-widget__empty">
      <p class="cdek-widget__hint">Выберите способ получения, чтобы рассчитать стоимость доставки</p>
      <button
        class="cdek-widget__btn"
        data-testid="cdek-open-selector"
        :disabled="isLoading"
        @click="openWidget"
      >
        {{ isLoading ? 'Загрузка...' : 'Выбрать доставку СДЭК' }}
      </button>
    </div>

    <div v-else class="cdek-widget__selected" data-testid="cdek-selected-delivery">
      <div class="cdek-widget__info">
        <span class="cdek-widget__mode">
          {{ selectedDelivery.delivery_mode === 'PVZ' ? 'Пункт выдачи' : 'Курьерская доставка' }}
        </span>
        <p class="cdek-widget__address">{{ selectedDelivery.shipping_address }}</p>
        <p class="cdek-widget__tariff">{{ selectedDelivery.tariff_name }}</p>
        <p class="cdek-widget__period">
          Срок: {{ selectedDelivery.period_min || '-' }}-{{ selectedDelivery.period_max || '-' }} дн.
        </p>
      </div>
      <div class="cdek-widget__price">{{ formatPrice(selectedDelivery.price) }} ₽</div>
      <button class="cdek-widget__change" data-testid="cdek-change-delivery" @click="openWidget">Изменить</button>
    </div>

    <div v-if="loadError" class="cdek-widget__error" data-testid="cdek-widget-error">
      Не удалось загрузить виджет СДЭК. Проверьте подключение к интернету и повторите попытку.
    </div>

    <!-- Hidden container required by the official widget -->
    <div id="cdek-widget-container" class="cdek-widget__container" data-testid="cdek-widget-container"></div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue';

const props = defineProps({
  items: { type: Array, required: true },
  modelValue: { type: Object, default: null },
});

const emit = defineEmits(['update:modelValue']);

const WIDGET_SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/@cdek-it/widget@3';
const WIDGET_CONTAINER_ID = 'cdek-widget-container';
const DEFAULT_LOCATION = 'Москва';

const selectedDelivery = computed(() => props.modelValue);
const widgetInstance = ref(null);
const scriptLoaded = ref(false);
const loadError = ref(false);
const isLoading = ref(false);
const detectedLocation = ref(null);

function formatPrice(price) {
  return Number(price).toLocaleString('ru-RU');
}

function normalizeDelivery(type, tariff, point) {
  const isDoor = type === 'door';
  const code = point?.code;
  const location = point?.location || {};

  return {
    tariff_code: tariff?.tariff_code,
    tariff_name: tariff?.tariff_name,
    delivery_mode: isDoor ? 'DOOR' : 'PVZ',
    delivery_point: !isDoor ? code : null,
    to_location: isDoor
      ? {
          code: location.city_code,
          city: location.city,
          address: location.address,
        }
      : null,
    from_location: null,
    price: tariff?.delivery_sum,
    period_min: tariff?.period_min,
    period_max: tariff?.period_max,
    shipping_address: isDoor
      ? location.address
      : `ПВЗ ${code}, ${location.address}`,
  };
}

function onChoose(type, tariff, point) {
  emit('update:modelValue', normalizeDelivery(type, tariff, point));
  widgetInstance.value?.destroy?.();
  widgetInstance.value = null;
}

function buildGoods() {
  return props.items.map((item) => {
    const product = item.product || item;
    return {
      weight: (product.weight_grams || 1000) / 1000,
      length: product.length_cm || 10,
      width: product.width_cm || 10,
      height: product.height_cm || 10,
    };
  });
}

function getApiKey() {
  return import.meta.env.VITE_YANDEX_MAPS_API_KEY || '';
}

function buildWidgetOptions() {
  return {
    root: WIDGET_CONTAINER_ID,
    apiKey: getApiKey(),
    servicePath: '/api/v1/cdek/widget-service/',
    popup: true,
    lang: 'rus',
    defaultLocation: detectedLocation.value || DEFAULT_LOCATION,
    goods: buildGoods(),
    onChoose,
  };
}

function detectUserLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) {
      resolve(DEFAULT_LOCATION);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { longitude, latitude } = position.coords;
        resolve([longitude, latitude]);
      },
      () => {
        resolve(DEFAULT_LOCATION);
      },
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 600000 }
    );
  });
}

async function loadScript() {
  if (typeof window === 'undefined') return;
  if (window.CDEKWidget || scriptLoaded.value) return;

  isLoading.value = true;
  loadError.value = false;

  try {
    await new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = WIDGET_SCRIPT_URL;
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Failed to load CDEK widget script'));
      document.head.appendChild(script);
    });
    scriptLoaded.value = true;
  } catch {
    loadError.value = true;
  } finally {
    isLoading.value = false;
  }
}

async function openWidget() {
  if (widgetInstance.value) {
    widgetInstance.value.destroy?.();
    widgetInstance.value = null;
  }

  isLoading.value = true;
  loadError.value = false;

  if (!detectedLocation.value) {
    detectedLocation.value = await detectUserLocation();
  }

  await loadScript();

  if (!window.CDEKWidget) {
    loadError.value = true;
    isLoading.value = false;
    return;
  }

  if (!getApiKey()) {
    loadError.value = true;
    isLoading.value = false;
    return;
  }

  try {
    widgetInstance.value = new window.CDEKWidget(buildWidgetOptions());
  } catch {
    loadError.value = true;
  } finally {
    isLoading.value = false;
  }
}

onUnmounted(() => {
  if (widgetInstance.value) {
    widgetInstance.value.destroy?.();
    widgetInstance.value = null;
  }
});
</script>

<style scoped>
.cdek-widget {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cdek-widget__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-text);
  margin: 0;
}

.cdek-widget__empty {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cdek-widget__hint {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.cdek-widget__btn {
  padding: 12px 16px;
  border-radius: 12px;
  background: var(--color-primary);
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  width: 100%;
}

.cdek-widget__btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cdek-widget__selected {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border-radius: 12px;
  background: var(--color-bg);
}

.cdek-widget__mode {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-primary);
  text-transform: uppercase;
}

.cdek-widget__address {
  font-size: 14px;
  color: var(--color-text);
  margin: 0;
}

.cdek-widget__tariff {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.cdek-widget__period {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.cdek-widget__price {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.cdek-widget__change {
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 8px;
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  font-size: 13px;
  cursor: pointer;
}

.cdek-widget__error {
  padding: 12px;
  border-radius: 10px;
  background: #fff0f0;
  color: var(--color-danger);
  font-size: 13px;
}

.cdek-widget__container {
  position: fixed;
  inset: 0;
  z-index: 1000;
  pointer-events: auto;
}

.cdek-widget__container:empty {
  pointer-events: none;
}
</style>
