import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import Skeleton from '../components/Skeleton.vue';
import SkeletonProductCard from '../components/SkeletonProductCard.vue';

describe('Skeleton.vue', () => {
  it('рендерит skeleton с заданными размерами', () => {
    const wrapper = mount(Skeleton, {
      props: { width: '100px', height: '20px' },
    });
    const el = wrapper.find('.skeleton');
    expect(el.exists()).toBe(true);
    expect(el.element.style.width).toBe('100px');
    expect(el.element.style.height).toBe('20px');
  });

  it('рендерит круглый skeleton', () => {
    const wrapper = mount(Skeleton, {
      props: { circle: true, width: '40px', height: '40px' },
    });
    expect(wrapper.find('.skeleton--circle').exists()).toBe(true);
  });
});

describe('SkeletonProductCard.vue', () => {
  it('рендерит все элементы карточки', () => {
    const wrapper = mount(SkeletonProductCard);
    const skeletons = wrapper.findAll('.skeleton');
    expect(skeletons.length).toBe(5); // image + price + 2 name lines + btn
  });
});
