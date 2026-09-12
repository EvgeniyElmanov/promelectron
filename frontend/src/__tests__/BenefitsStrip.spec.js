import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import BenefitsStrip from '@/components/home/BenefitsStrip.vue';

describe('BenefitsStrip', () => {
  it('renders section with 6 benefit items', () => {
    const wrapper = mount(BenefitsStrip);
    expect(wrapper.find('[data-testid="benefits-strip"]').exists()).toBe(true);
    expect(wrapper.findAll('.benefits-strip__item')).toHaveLength(6);
  });

  it('renders titles and descriptions', () => {
    const wrapper = mount(BenefitsStrip);
    expect(wrapper.text()).toContain('Официальная гарантия');
    expect(wrapper.text()).toContain('Доставка по РФ');
  });
});
