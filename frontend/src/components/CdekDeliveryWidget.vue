<template>
  <div class="cdek-widget" data-testid="cdek-delivery-widget">
    <h3 class="cdek-widget__title">Доставка СДЭК</h3>

    <div v-if="!selectedDelivery" class="cdek-widget__empty">
      <p class="cdek-widget__hint">Выберите способ получения, чтобы рассчитать стоимость доставки</p>
      <button class="cdek-widget__btn" data-testid="cdek-open-selector" @click="openSelector">
        Выбрать доставку СДЭК
      </button>
    </div>

    <div v-else class="cdek-widget__selected">
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
      <button class="cdek-widget__change" @click="openSelector">Изменить</button>
    </div>

    <!-- Modal -->
    <div v-if="isOpen" class="cdek-widget__modal" @click.self="closeSelector">
      <div class="cdek-widget__modal-content">
        <div class="cdek-widget__modal-header">
          <h4>Выбор доставки СДЭК</h4>
          <button class="cdek-widget__close" @click="closeSelector">&times;</button>
        </div>

        <div class="cdek-widget__modal-body">
          <!-- Mode selection -->
          <div class="cdek-widget__modes">
            <label class="cdek-widget__mode-option" :class="{ active: mode === 'PVZ' }">
              <input v-model="mode" type="radio" value="PVZ" />
              <span>До ПВЗ</span>
            </label>
            <label class="cdek-widget__mode-option" :class="{ active: mode === 'DOOR' }">
              <input v-model="mode" type="radio" value="DOOR" />
              <span>Курьером до двери</span>
            </label>
          </div>

          <!-- City -->
          <div class="cdek-widget__field">
            <label>Город</label>
            <input
              v-model="cityQuery"
              type="text"
              placeholder="Начните вводить город"
              data-testid="cdek-city-input"
              @input="debouncedSearchCities"
            />
            <ul v-if="cities.length" class="cdek-widget__suggestions">
              <li
                v-for="city in cities"
                :key="city.code"
                @click="selectCity(city)"
              >
                {{ city.city }}
              </li>
            </ul>
          </div>

          <!-- PVZ selection -->
          <div v-if="mode === 'PVZ' && selectedCity" class="cdek-widget__field">
            <label>Пункт выдачи</label>
            <select v-model="selectedPvzCode" data-testid="cdek-pvz-select" @change="selectPvz">
              <option value="">Выберите ПВЗ</option>
              <option v-for="pvz in pvzList" :key="pvz.code" :value="pvz.code">
                {{ pvz.name }} — {{ pvz.location?.address }}
              </option>
            </select>
          </div>

          <!-- Door address -->
          <div v-if="mode === 'DOOR' && selectedCity" class="cdek-widget__field">
            <label>Адрес доставки</label>
            <input
              v-model="doorAddress"
              type="text"
              placeholder="ул. Ленина, д. 1, кв. 10"
              data-testid="cdek-door-address"
            />
          </div>

          <button
            class="cdek-widget__btn cdek-widget__btn--calc"
            data-testid="cdek-calculate"
            :disabled="!canCalculate || calculating"
            @click="calculate"
          >
            {{ calculating ? 'Расчёт...' : 'Рассчитать доставку' }}
          </button>

          <!-- Tariffs -->
          <div v-if="tariffs.length" class="cdek-widget__tariffs">
            <label
              v-for="tariff in tariffs"
              :key="tariff.tariff_code"
              class="cdek-widget__tariff-option"
              :class="{ active: selectedTariff?.tariff_code === tariff.tariff_code }"
            >
              <input
                v-model="selectedTariff"
                type="radio"
                :value="tariff"
              />
              <div class="cdek-widget__tariff-info">
                <span class="cdek-widget__tariff-name">{{ tariff.tariff_name }}</span>
                <span class="cdek-widget__tariff-period">
                  {{ tariff.period_min }}-{{ tariff.period_max }} дн.
                </span>
              </div>
              <span class="cdek-widget__tariff-price">{{ formatPrice(tariff.price) }} ₽</span>
            </label>
          </div>

          <button
            v-if="selectedTariff"
            class="cdek-widget__btn cdek-widget__btn--confirm"
            data-testid="cdek-confirm"
            @click="confirm"
          >
            Подтвердить выбор
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import api from '@/services/api';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  items: { type: Array, required: true },
  modelValue: { type: Object, default: null },
});

const emit = defineEmits(['update:modelValue']);

const { add: toast } = useToast();

const isOpen = ref(false);
const mode = ref('PVZ');
const cityQuery = ref('');
const cities = ref([]);
const selectedCity = ref(null);
const selectedPvzCode = ref('');
const pvzList = ref([]);
const doorAddress = ref('');
const calculating = ref(false);
const tariffs = ref([]);
const selectedTariff = ref(null);

const selectedDelivery = computed(() => props.modelValue);

const supplierId = computed(() => {
  const firstItem = props.items[0];
  return firstItem?.product?.supplier_id || firstItem?.supplier_id;
});

const canCalculate = computed(() => {
  if (!selectedCity.value) return false;
  if (mode.value === 'PVZ') return !!selectedPvzCode.value;
  return !!doorAddress.value.trim();
});

let debounceTimer = null;

function formatPrice(price) {
  return Number(price).toLocaleString('ru-RU');
}

function openSelector() {
  isOpen.value = true;
}

function closeSelector() {
  isOpen.value = false;
}

async function debouncedSearchCities() {
  clearTimeout(debounceTimer);
  cities.value = [];
  selectedCity.value = null;
  if (!cityQuery.value.trim()) return;
  debounceTimer = setTimeout(searchCities, 400);
}

async function searchCities() {
  try {
    const { data } = await api.get('/cdek/suggest-cities/', {
      params: { name: cityQuery.value },
    });
    cities.value = Array.isArray(data) ? data : [];
  } catch (err) {
    console.error('Failed to search cities:', err);
  }
}

async function selectCity(city) {
  selectedCity.value = city;
  cityQuery.value = city.city;
  cities.value = [];
  selectedPvzCode.value = '';
  pvzList.value = [];
  tariffs.value = [];
  selectedTariff.value = null;

  if (mode.value === 'PVZ') {
    await loadPvz(city.code);
  }
}

async function loadPvz(cityCode) {
  try {
    const { data } = await api.get('/cdek/pvz/', {
      params: { city_code: cityCode },
    });
    pvzList.value = Array.isArray(data) ? data : [];
  } catch (err) {
    console.error('Failed to load PVZ:', err);
    toast('Не удалось загрузить список ПВЗ', 'error');
  }
}

function selectPvz() {
  tariffs.value = [];
  selectedTariff.value = null;
}

async function calculate() {
  if (!supplierId.value) {
    toast('Не удалось определить поставщика товара', 'error');
    return;
  }

  calculating.value = true;
  try {
    const payload = {
      items: props.items.map(item => ({
        product_id: item.product_id || item.product?.id,
        quantity: item.quantity,
        weight_grams: item.product?.weight_grams || 1000,
        length_cm: item.product?.length_cm,
        width_cm: item.product?.width_cm,
        height_cm: item.product?.height_cm,
      })),
      supplier_id: supplierId.value,
    };

    if (mode.value === 'PVZ') {
      payload.delivery_point = selectedPvzCode.value;
    } else {
      payload.to_location = {
        code: selectedCity.value.code,
        city: selectedCity.value.city,
        address: doorAddress.value,
      };
    }

    const { data } = await api.post('/cdek/calculate/', payload);
    tariffs.value = data.tariffs || [];
    if (!tariffs.value.length) {
      toast('Нет доступных тарифов для выбранного направления', 'error');
    }
  } catch (err) {
    console.error('Failed to calculate delivery:', err);
    toast(err.response?.data?.detail || 'Не удалось рассчитать доставку', 'error');
  } finally {
    calculating.value = false;
  }
}

function confirm() {
  const tariff = selectedTariff.value;
  if (!tariff) return;

  const pvz = pvzList.value.find(p => p.code === selectedPvzCode.value);
  const shippingAddress = mode.value === 'PVZ'
    ? `ПВЗ ${selectedPvzCode.value}${pvz ? `, ${pvz.location?.address || pvz.name}` : ''}`
    : doorAddress.value;

  emit('update:modelValue', {
    tariff_code: tariff.tariff_code,
    tariff_name: tariff.tariff_name,
    delivery_mode: mode.value,
    delivery_point: mode.value === 'PVZ' ? selectedPvzCode.value : null,
    to_location: mode.value === 'DOOR' ? {
      code: selectedCity.value.code,
      city: selectedCity.value.city,
      address: doorAddress.value,
    } : null,
    from_location: null,
    price: tariff.price,
    period_min: tariff.period_min,
    period_max: tariff.period_max,
    shipping_address: shippingAddress,
  });

  closeSelector();
}

watch(mode, () => {
  selectedPvzCode.value = '';
  pvzList.value = [];
  tariffs.value = [];
  selectedTariff.value = null;
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

.cdek-widget__btn--calc {
  margin-top: 12px;
}

.cdek-widget__btn--confirm {
  margin-top: 12px;
  background: #0d7a3e;
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

.cdek-widget__modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}

.cdek-widget__modal-content {
  background: var(--color-bg-white);
  border-radius: 16px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.cdek-widget__modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid var(--color-border);
}

.cdek-widget__modal-header h4 {
  margin: 0;
  font-size: 16px;
}

.cdek-widget__close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.cdek-widget__modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.cdek-widget__modes {
  display: flex;
  gap: 8px;
}

.cdek-widget__mode-option {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px;
  border-radius: 10px;
  border: 2px solid var(--color-border);
  cursor: pointer;
  font-size: 14px;
}

.cdek-widget__mode-option.active {
  border-color: var(--color-primary);
  background: var(--color-bg);
}

.cdek-widget__mode-option input {
  display: none;
}

.cdek-widget__field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.cdek-widget__field label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.cdek-widget__field input,
.cdek-widget__field select {
  padding: 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 15px;
  background: var(--color-bg-white);
}

.cdek-widget__suggestions {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  max-height: 160px;
  overflow-y: auto;
}

.cdek-widget__suggestions li {
  padding: 10px 12px;
  cursor: pointer;
  font-size: 14px;
}

.cdek-widget__suggestions li:hover {
  background: var(--color-bg);
}

.cdek-widget__tariffs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.cdek-widget__tariff-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 10px;
  border: 2px solid var(--color-border);
  cursor: pointer;
}

.cdek-widget__tariff-option.active {
  border-color: var(--color-primary);
}

.cdek-widget__tariff-option input {
  display: none;
}

.cdek-widget__tariff-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cdek-widget__tariff-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.cdek-widget__tariff-period {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.cdek-widget__tariff-price {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text);
}
</style>
