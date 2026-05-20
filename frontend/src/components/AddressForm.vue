<template>
  <div class="address-form">
    <div class="address-form__header">
      <label class="address-form__label">{{ label }}</label>
    </div>

    <div class="address-form__grid">
      <div class="address-field">
        <label class="address-field__label">Область / край / республика</label>
        <AutocompleteInput
          v-model="modelValue.region"
          field="region"
          :options="RUSSIAN_REGIONS"
          placeholder=""
          :testid="testidPrefix + 'region'"
          @select="onSuggestionSelect"
        />
      </div>

      <div class="address-field">
        <label class="address-field__label">Район / округ / район города</label>
        <AutocompleteInput
          v-model="modelValue.district"
          field="district"
          :context="suggestionContext"
          placeholder=""
          :testid="testidPrefix + 'district'"
          @select="onSuggestionSelect"
        />
      </div>

      <div class="address-field address-field--wide">
        <label class="address-field__label">Город / населённый пункт <span class="required">*</span></label>
        <AutocompleteInput
          v-model="modelValue.city"
          field="city"
          :options="RUSSIAN_CITIES"
          :context="suggestionContext"
          placeholder=""
          :testid="testidPrefix + 'city'"
          @select="onSuggestionSelect"
        />
      </div>

      <div class="address-field address-field--wide">
        <label class="address-field__label">Улица / проспект / переулок <span class="required">*</span></label>
        <AutocompleteInput
          v-model="modelValue.street"
          field="street"
          :context="suggestionContext"
          placeholder=""
          :testid="testidPrefix + 'street'"
          @select="onSuggestionSelect"
        />
      </div>

      <div class="address-field">
        <label class="address-field__label">Дом / строение / корпус <span class="required">*</span></label>
        <input
          v-model="modelValue.house"
          type="text"
          placeholder=""
          class="address-field__input"
          :data-testid="testidPrefix + 'house'"
        />
      </div>

      <div class="address-field">
        <label class="address-field__label">Квартира / офис / этаж</label>
        <input
          v-model="modelValue.apartment"
          type="text"
          placeholder=""
          class="address-field__input"
          :data-testid="testidPrefix + 'apartment'"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RUSSIAN_REGIONS } from '@/data/russianRegions';
import { RUSSIAN_CITIES } from '@/data/russianCities';
import AutocompleteInput from './AutocompleteInput.vue';

const props = defineProps({
  modelValue: { type: Object, required: true },
  label: { type: String, default: 'Адрес доставки' },
  testidPrefix: { type: String, default: 'address-' },
});

const emit = defineEmits(['update:modelValue']);

const suggestionContext = computed(() => ({
  region: props.modelValue.region || '',
  city: props.modelValue.city || '',
}));

function onSuggestionSelect(item) {
  const merged = { ...props.modelValue };
  if (item.region) merged.region = item.region;
  if (item.district) merged.district = item.district;
  if (item.city) merged.city = item.city;
  if (item.street) merged.street = item.street;
  if (item.house) merged.house = item.house;
  emit('update:modelValue', merged);
}
</script>

<style scoped>
.address-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.address-form__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.address-form__label {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text);
}

.address-form__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.address-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.address-field--wide {
  grid-column: span 2;
}

.address-field__label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
}

.address-field__input {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--color-border);
  font-size: 15px;
  background: var(--color-bg-white);
  transition: border-color 0.15s;
}

.address-field__input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.required {
  color: var(--color-danger);
}

@media (min-width: 768px) {
  .address-form__grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
