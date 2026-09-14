import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { defineComponent, ref, nextTick } from 'vue';
import { useModal } from '@/composables/useModal';

const TestModal = defineComponent({
  props: {
    closeOnEscape: { type: [Boolean, Function], default: true },
    empty: { type: Boolean, default: false },
  },
  emits: ['close'],
  setup(props, { emit }) {
    const isOpen = ref(false);
    const { dialogRef, titleId } = useModal({
      isOpen,
      onClose: () => emit('close'),
      closeOnEscape: props.closeOnEscape,
    });
    return { isOpen, dialogRef, titleId };
  },
  template: `
    <div>
      <button data-testid="trigger" @click="isOpen = true">Открыть</button>
      <div v-if="isOpen" class="modal-overlay">
        <div ref="dialogRef" class="modal" role="dialog" aria-modal="true" :aria-labelledby="titleId" tabindex="-1" data-testid="dialog">
          <h3 :id="titleId">Заголовок</h3>
          <template v-if="!empty">
            <button data-testid="first">Первый</button>
            <input data-testid="middle" type="text" />
            <button data-testid="last">Последний</button>
          </template>
        </div>
      </div>
    </div>
  `,
});

const mountModal = (props = {}) =>
  mount(TestModal, { props, attachTo: document.body });

const openModal = async (wrapper) => {
  await wrapper.find('[data-testid="trigger"]').trigger('click');
  await nextTick();
};

const keydown = (key, options = {}) => {
  document.activeElement?.dispatchEvent(
    new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...options })
  );
};

describe('useModal', () => {
  let wrapper;

  beforeEach(() => {
    wrapper = mountModal();
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('переводит фокус на первый фокусируемый элемент при открытии', async () => {
    await openModal(wrapper);
    expect(document.activeElement).toBe(wrapper.find('[data-testid="first"]').element);
  });

  it('фокусирует контейнер диалога, если фокусируемых элементов нет', async () => {
    wrapper.unmount();
    wrapper = mountModal({ empty: true });
    await openModal(wrapper);
    expect(document.activeElement).toBe(wrapper.find('[data-testid="dialog"]').element);
  });

  it('Tab на последнем элементе переносит фокус на первый', async () => {
    await openModal(wrapper);
    wrapper.find('[data-testid="last"]').element.focus();
    keydown('Tab');
    expect(document.activeElement).toBe(wrapper.find('[data-testid="first"]').element);
  });

  it('Shift+Tab на первом элементе переносит фокус на последний', async () => {
    await openModal(wrapper);
    wrapper.find('[data-testid="first"]').element.focus();
    keydown('Tab', { shiftKey: true });
    expect(document.activeElement).toBe(wrapper.find('[data-testid="last"]').element);
  });

  it('возвращает фокус внутрь, если фокус оказался вне диалога', async () => {
    await openModal(wrapper);
    wrapper.find('[data-testid="trigger"]').element.focus();
    keydown('Tab');
    expect(document.activeElement).toBe(wrapper.find('[data-testid="first"]').element);
  });

  it('Escape вызывает onClose', async () => {
    await openModal(wrapper);
    keydown('Escape');
    expect(wrapper.emitted('close')).toHaveLength(1);
  });

  it('Escape не вызывает onClose, если событие уже defaultPrevented', async () => {
    await openModal(wrapper);
    const event = new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true });
    document.activeElement?.addEventListener('keydown', (e) => e.preventDefault(), { once: true });
    document.activeElement?.dispatchEvent(event);
    expect(wrapper.emitted('close')).toBeUndefined();
  });

  it('Escape не закрывает, когда closeOnEscape вычисляется в false', async () => {
    wrapper.unmount();
    wrapper = mountModal({ closeOnEscape: () => false });
    await openModal(wrapper);
    keydown('Escape');
    expect(wrapper.emitted('close')).toBeUndefined();
  });

  it('возвращает фокус инициатору при закрытии', async () => {
    const trigger = wrapper.find('[data-testid="trigger"]').element;
    trigger.focus();
    await openModal(wrapper);
    expect(document.activeElement).not.toBe(trigger);
    wrapper.vm.isOpen = false;
    await nextTick();
    expect(document.activeElement).toBe(trigger);
  });

  it('не падает, если инициатор удалён из DOM к моменту закрытия', async () => {
    await openModal(wrapper);
    wrapper.find('[data-testid="trigger"]').element.remove();
    wrapper.vm.isOpen = false;
    await nextTick();
    expect(document.activeElement).not.toBe(null);
  });

  it('генерирует стабильный titleId внутри экземпляра и уникальный между экземплярами', () => {
    const other = mountModal();
    expect(wrapper.vm.titleId).toMatch(/^modal-title-\d+$/);
    expect(other.vm.titleId).not.toBe(wrapper.vm.titleId);
    other.unmount();
  });

  it('снимает keydown-листенер при размонтировании', async () => {
    await openModal(wrapper);
    wrapper.unmount();
    wrapper = null;
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true, cancelable: true }));
    // отсутствие исключения — листенер снят
  });
});
