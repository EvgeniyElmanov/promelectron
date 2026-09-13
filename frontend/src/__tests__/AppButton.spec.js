import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import AppButton from '@/components/ui/AppButton.vue';

describe('AppButton.vue', () => {
  it('рендерит slot и primary/md по умолчанию', () => {
    const wrapper = mount(AppButton, { slots: { default: 'В корзину' } });
    expect(wrapper.text()).toBe('В корзину');
    expect(wrapper.classes()).toContain('app-button--primary');
    expect(wrapper.classes()).toContain('app-button--md');
  });

  it('применяет variant secondary и ghost', () => {
    expect(mount(AppButton, { props: { variant: 'secondary' } }).classes()).toContain(
      'app-button--secondary',
    );
    expect(mount(AppButton, { props: { variant: 'ghost' } }).classes()).toContain(
      'app-button--ghost',
    );
  });

  it('применяет size sm и block', () => {
    const wrapper = mount(AppButton, { props: { size: 'sm', block: true } });
    expect(wrapper.classes()).toContain('app-button--sm');
    expect(wrapper.classes()).toContain('app-button--block');
  });

  it('disabled ставит атрибут disabled', () => {
    const wrapper = mount(AppButton, { props: { disabled: true } });
    expect(wrapper.attributes('disabled')).toBeDefined();
  });

  it('loading блокирует кнопку и добавляет класс', () => {
    const wrapper = mount(AppButton, { props: { loading: true } });
    expect(wrapper.attributes('disabled')).toBeDefined();
    expect(wrapper.classes()).toContain('app-button--loading');
  });

  it('эмитит click', async () => {
    const wrapper = mount(AppButton);
    await wrapper.trigger('click');
    expect(wrapper.emitted('click')).toHaveLength(1);
  });

  it('type=button по умолчанию и проксирует type=submit', () => {
    expect(mount(AppButton).attributes('type')).toBe('button');
    expect(mount(AppButton, { props: { type: 'submit' } }).attributes('type')).toBe('submit');
  });

  it('применяет variant danger', () => {
    expect(mount(AppButton, { props: { variant: 'danger' } }).classes()).toContain(
      'app-button--danger',
    );
  });
});
