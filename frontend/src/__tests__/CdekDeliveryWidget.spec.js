import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import CdekDeliveryWidget from '../components/CdekDeliveryWidget.vue';

describe('CdekDeliveryWidget.vue', () => {
  beforeEach(() => {
    window.CDEKWidget = class MockCDEKWidget {
      constructor() {
        this.destroy = vi.fn();
      }
    };
  });

  afterEach(() => {
    delete window.CDEKWidget;
    document.querySelectorAll('script').forEach((script) => {
      if (script.src.includes('@cdek-it/widget')) {
        script.remove();
      }
    });
  });

  it('рендерит кнопку выбора доставки', () => {
    const wrapper = mount(CdekDeliveryWidget, {
      props: { items: [], modelValue: null },
    });
    expect(wrapper.find('[data-testid="cdek-open-selector"]').exists()).toBe(true);
  });

  it('показывает выбранную доставку', () => {
    const wrapper = mount(CdekDeliveryWidget, {
      props: {
        items: [],
        modelValue: {
          tariff_code: 136,
          tariff_name: 'Экспресс-экспедиция',
          delivery_mode: 'PVZ',
          delivery_point: 'TEST1',
          price: 350,
          period_min: 1,
          period_max: 3,
          shipping_address: 'ПВЗ TEST1, ул. Тестовая, 1',
        },
      },
    });
    expect(wrapper.text()).toContain('Пункт выдачи');
    expect(wrapper.text()).toContain('ПВЗ TEST1, ул. Тестовая, 1');
    expect(wrapper.text()).toContain('350 ₽');
  });

  it('создаёт виджет с корректными опциями при клике', async () => {
    const constructorSpy = vi.spyOn(window, 'CDEKWidget');

    const wrapper = mount(CdekDeliveryWidget, {
      props: { items: [], modelValue: null },
    });
    await wrapper.find('[data-testid="cdek-open-selector"]').trigger('click');
    await flushPromises();

    expect(constructorSpy).toHaveBeenCalledTimes(1);
    const options = constructorSpy.mock.calls[0][0];
    expect(options.servicePath).toBe('/api/v1/cdek/widget-service/');
    expect(options.popup).toBe(true);
    expect(options.lang).toBe('rus');
    expect(options.defaultLocation).toBe('Москва');

    constructorSpy.mockRestore();
  });

  it('нормализует выбор ПВЗ в формат CdekDeliveryIn', async () => {
    window.CDEKWidget = vi.fn(function (options) {
      this.destroy = vi.fn();
      setTimeout(() => {
        options.onChoose('PVZ', {
          tariff_code: 136,
          tariff_name: 'Экспресс-экспедиция',
          delivery_sum: 350,
          period_min: 1,
          period_max: 3,
        }, {
          code: 'TEST1',
          location: { city_code: 44, city: 'Москва', address: 'ул. Тестовая, 1' },
        });
      }, 0);
    });

    const wrapper = mount(CdekDeliveryWidget, {
      props: {
        items: [{ product: { weight_grams: 1000, length_cm: 10, width_cm: 10, height_cm: 10 } }],
        modelValue: null,
      },
    });

    await wrapper.find('[data-testid="cdek-open-selector"]').trigger('click');
    await flushPromises();
    await new Promise((resolve) => setTimeout(resolve, 10));

    const events = wrapper.emitted('update:modelValue');
    expect(events).toHaveLength(1);
    expect(events[0][0]).toEqual({
      tariff_code: 136,
      tariff_name: 'Экспресс-экспедиция',
      delivery_mode: 'PVZ',
      delivery_point: 'TEST1',
      to_location: null,
      from_location: null,
      price: 350,
      period_min: 1,
      period_max: 3,
      shipping_address: 'ПВЗ TEST1, ул. Тестовая, 1',
    });
  });

  it('нормализует выбор курьерской доставки в формат CdekDeliveryIn', async () => {
    window.CDEKWidget = vi.fn(function (options) {
      this.destroy = vi.fn();
      setTimeout(() => {
        options.onChoose('door', {
          tariff_code: 137,
          tariff_name: 'До двери',
          delivery_sum: 500,
          period_min: 2,
          period_max: 4,
        }, {
          location: { city_code: 44, city: 'Москва', address: 'ул. Ленина, 1' },
        });
      }, 0);
    });

    const wrapper = mount(CdekDeliveryWidget, {
      props: { items: [], modelValue: null },
    });

    await wrapper.find('[data-testid="cdek-open-selector"]').trigger('click');
    await flushPromises();
    await new Promise((resolve) => setTimeout(resolve, 10));

    const events = wrapper.emitted('update:modelValue');
    expect(events).toHaveLength(1);
    expect(events[0][0]).toEqual({
      tariff_code: 137,
      tariff_name: 'До двери',
      delivery_mode: 'DOOR',
      delivery_point: null,
      to_location: { code: 44, city: 'Москва', address: 'ул. Ленина, 1' },
      from_location: null,
      price: 500,
      period_min: 2,
      period_max: 4,
      shipping_address: 'ул. Ленина, 1',
    });
  });
});
