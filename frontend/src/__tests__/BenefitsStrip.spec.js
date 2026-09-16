import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import BenefitsStrip from '@/components/home/BenefitsStrip.vue';

describe('BenefitsStrip (D-07)', () => {
  it('renders section with 4 benefit items по растру', () => {
    const wrapper = mount(BenefitsStrip);
    expect(wrapper.find('[data-testid="benefits-strip"]').exists()).toBe(true);
    expect(wrapper.findAll('.benefits-strip__item')).toHaveLength(4);
  });

  it('renders titles и descriptions по макету', () => {
    const wrapper = mount(BenefitsStrip);
    expect(wrapper.text()).toContain('Официальная гарантия');
    expect(wrapper.text()).toContain('Доставка по всей России');
    expect(wrapper.text()).toContain('Оплата удобным способом');
    expect(wrapper.text()).toContain('Поддержка 24/7');
  });
});
