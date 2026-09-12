import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import AppBadge from '@/components/ui/AppBadge.vue';

describe('AppBadge.vue', () => {
  it('рендерит label и variant-класс', () => {
    const wrapper = mount(AppBadge, { props: { variant: 'sale', label: 'SALE' } });
    expect(wrapper.text()).toBe('SALE');
    expect(wrapper.classes()).toContain('app-badge--sale');
  });

  it.each(['sale', 'new', 'hit', 'in-stock', 'out-of-stock'])(
    'поддерживает variant %s',
    (variant) => {
      const wrapper = mount(AppBadge, { props: { variant } });
      expect(wrapper.classes()).toContain(`app-badge--${variant}`);
    },
  );

  it('рендерит slot вместо label', () => {
    const wrapper = mount(AppBadge, {
      props: { variant: 'out-of-stock' },
      slots: { default: 'Нет в наличии' },
    });
    expect(wrapper.text()).toBe('Нет в наличии');
  });
});
