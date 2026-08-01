import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import FilterPanel from '@/components/FilterPanel.vue';

const FACETS = [
  {
    code: 'categories.lvl0',
    name: 'Категории',
    value_type: 'enum',
    values: [{ value: 'Электроника', count: 12 }],
  },
  {
    code: 'categories.lvl1',
    name: 'Подкатегории',
    value_type: 'enum',
    values: [{ value: 'Электроника > Смартфоны', count: 7 }],
  },
  {
    code: 'price',
    name: 'Цена',
    value_type: 'number',
    stats: { min: 100, max: 5000 },
  },
  {
    code: 'brand',
    name: 'Бренд',
    value_type: 'enum',
    values: [
      { value: 'Samsung', count: 5 },
      { value: 'LG', count: 3 },
    ],
  },
  {
    code: 'power',
    name: 'Мощность',
    value_type: 'number',
    unit: 'Вт',
    stats: { min: 10, max: 2000 },
  },
];

const CATEGORIES = [
  { id: 1, name: 'Электроника', parent_id: null },
  { id: 2, name: 'Смартфоны', parent_id: 1 },
];

function mountPanel(props = {}) {
  return mount(FilterPanel, {
    props: {
      facets: FACETS,
      selected: new Map(),
      priceRange: { min: null, max: null },
      categoryId: null,
      categoryOptions: CATEGORIES,
      ...props,
    },
  });
}

describe('FilterPanel.vue', () => {
  it('рендерит панель и все группы фасетов', () => {
    const wrapper = mountPanel();
    expect(wrapper.find('[data-testid="filter-panel"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="filter-group-brand"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="filter-group-power"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="filter-group-price"]').exists()).toBe(true);
  });

  it('рендерит значения фасета со счётчиками (disjunctive counts от backend)', () => {
    const wrapper = mountPanel();
    const group = wrapper.find('[data-testid="filter-group-brand"]');
    expect(group.text()).toContain('Samsung');
    expect(group.text()).toContain('(5)');
    expect(group.text()).toContain('LG');
    expect(group.text()).toContain('(3)');
    expect(wrapper.find('[data-testid="filter-value-brand-0"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="filter-value-brand-1"]').exists()).toBe(true);
  });

  it('клик по чекбоксу эмитит toggle(code, value)', async () => {
    const wrapper = mountPanel();
    await wrapper.find('[data-testid="filter-value-brand-0"]').setValue(true);
    expect(wrapper.emitted('toggle')).toEqual([['brand', 'Samsung']]);
  });

  it('выбранное значение отображается отмеченным чекбоксом', () => {
    const wrapper = mountPanel({ selected: new Map([['brand', new Set(['LG'])]]) });
    const checkbox = wrapper.find('[data-testid="filter-value-brand-1"]');
    expect(checkbox.element.checked).toBe(true);
  });

  it('дерево категорий строится из lvl0/lvl1 (путь «Root > Child»)', () => {
    const wrapper = mountPanel();
    const group = wrapper.find('[data-testid="filter-group-categories"]');
    expect(group.text()).toContain('Электроника');
    expect(group.text()).toContain('Смартфоны');
  });

  it('клик по категории эмитит category с id из справочника (имя → id)', async () => {
    const wrapper = mountPanel();
    await wrapper.find('[data-testid="filter-category-2"]').trigger('click');
    expect(wrapper.emitted('category')).toEqual([[2]]);
  });

  it('повторный клик по активной категории снимает фильтр (category null)', async () => {
    const wrapper = mountPanel({ categoryId: 2 });
    await wrapper.find('[data-testid="filter-category-2"]').trigger('click');
    expect(wrapper.emitted('category')).toEqual([[null]]);
  });

  it('цена: apply эмитит price с clamp по stats {min,max}', async () => {
    const wrapper = mountPanel();
    await wrapper.find('[data-testid="filter-price-min"]').setValue(50); // ниже stats.min=100
    await wrapper.find('[data-testid="filter-price-max"]').setValue(9000); // выше stats.max=5000
    await wrapper.find('[data-testid="filter-apply"]').trigger('click');
    expect(wrapper.emitted('price')).toEqual([[{ min: 100, max: 5000 }]]);
  });

  it('числовой фасет: apply эмитит range(code, {min, max}) с clamp', async () => {
    const wrapper = mountPanel();
    await wrapper.find('[data-testid="filter-range-min-power"]').setValue(5); // ниже stats.min=10
    await wrapper.find('[data-testid="filter-range-max-power"]').setValue(1500);
    await wrapper.find('[data-testid="filter-range-apply-power"]').trigger('click');
    expect(wrapper.emitted('range')).toEqual([['power', { min: 10, max: 1500 }]]);
  });

  it('F002: числовое значение фасета отмечено, если selected содержит строку из URL', () => {
    const wrapper = mountPanel({
      facets: [
        {
          code: 'thickness',
          name: 'Толщина',
          value_type: 'enum',
          values: [
            { value: 2.5, count: 4 },
            { value: 3, count: 2 },
          ],
        },
      ],
      selected: new Map([['thickness', new Set(['2.5'])]]),
    });
    expect(wrapper.find('[data-testid="filter-value-thickness-0"]').element.checked).toBe(true);
    expect(wrapper.find('[data-testid="filter-value-thickness-1"]').element.checked).toBe(false);
  });

  it('кнопка сброса эмитит reset', async () => {
    const wrapper = mountPanel();
    await wrapper.find('[data-testid="filter-reset"]').trigger('click');
    expect(wrapper.emitted('reset')).toBeTruthy();
  });

  it('секции сворачиваются (нативный <details>)', async () => {
    const wrapper = mountPanel();
    const details = wrapper.find('[data-testid="filter-group-brand"]');
    expect(details.attributes('open')).toBeDefined();
    await details.find('summary').trigger('click');
    expect(details.attributes('open')).toBeUndefined();
  });
});
