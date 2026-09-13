# PLAN: design-cart-checkout-pr209 (этап 3-C, issue #249)

## 1. Goal

Перевести `Cart.vue` (§23), `Checkout.vue` (§24) и поля форм (§19) на токены и примитивы
дизайн-системы (`base.css`, `AppButton`), не меняя логику, API и ни один `data-testid`;
успех — vitest ≥439 зелёный, lint 0/0, E2E baseline 117 passed + те же 3 известных падения,
visual-smoke 11/11, ноль хардкод-цветов в изменённых файлах.

## 2. Steps

Порядок по spec Parallelization Plan: base.css формы → Cart.vue → Checkout.vue → тесты.
После каждого шага: `make -C "$WORKTREE" test-frontend` (соответствующий spec-файл) +
`make -C "$WORKTREE" lint-frontend`. Полный прогон в конце.

### Шаг 1. `frontend/src/assets/base.css` — глобальные классы форм §19 (D-02)

Добавить секцию «Forms (§19)» после существующего контента (в конец файла, после блока #171):

- `.field` — обёртка label + control + error (flex column, gap `var(--space-1)`).
- `.field__label` — caption-стиль лейбла (`--font-size-caption`/`body-sm`, `--color-text-secondary`).
- `.field__input` — height 48px, `border-radius: var(--radius-md)`,
  `padding: 0 var(--space-4)`, `border: 1px solid var(--color-border)`,
  `font-size: var(--font-size-body)`, `background: var(--color-bg-white)`,
  `color: var(--color-text)`, `width: 100%`.
- `.field__input:focus` — `border-color: var(--color-primary)` + focus-ring
  (`outline: none` + `box-shadow: 0 0 0 3px` на базе `--color-primary-light` / color-mix от primary).
- `.field__input--error` — `border-color: var(--color-error)`.
- `.field__input:disabled` — `background: var(--color-bg)`, `color: var(--color-text-secondary)`.
- `.field__error` — caption, `--color-error`.
- `.field__required` — `color: var(--color-danger)` (класс уже используется в Cart.vue:209,220,…
  без определения — заработает глобально).

**Инварианты:**
- Блок `base.css:125-132` (`font-size: 16px !important` на mobile input, issue #171) — НЕ трогать;
  на mobile он intended-перекроет font-size `.field__input`.
- Новые стили `.field__input` БЕЗ `!important`.

Проверка: `make lint-frontend` (stylelint/css не ломается); визуально классы нигде ещё не применяются
(select в Cart с `field__input` — no-op до шага 2, внешне не изменится: у него и так высота ~от контента).

### Шаг 2. `frontend/src/views/Cart.vue` — рестайл (D-03/04/05/07)

Template:

1. `checkout-button` (строка 278-286): `<button class="cart__checkout-btn">` →
   `<AppButton variant="primary" block :loading="creatingOrder" :disabled="…" data-testid="checkout-button" @click="createOrder">`.
   Текст: `creatingOrder ? 'Оформление...' : 'Оформить заказ'` — сохранить в слоте
   (loading-проп AppButton блокирует кнопку, но не меняет текст — текст остаётся на нашей стороне).
   AppButton рендерит `<button>`, click-fallthrough нативный (без defineEmits) — @click работает.
2. `recipient-new-button` (196-204) → `<AppButton variant="secondary" size="sm" data-testid="recipient-new-button" @click="…">`.
3. Empty-state: `<router-link to="/" class="cart__empty-btn">` →
   `<AppButton data-testid не нужен (не было) @click="router.push('/')">Перейти в каталог</AppButton>`.
   Смена тега a→button: проверить, что unit-тесты empty-state не ищут `router-link`
   (grep по Cart.spec.js — таких тестов нет; убедиться при правке).
4. Поля получателя (D-05): на все `.cart__recipient-field` input/select добавить класс `field__input`
   (+ на label — `field__label`, на обёртку — `field` рядом с `cart__recipient-field`, чтобы не
   ломать grid-раскладку). Select получателя уже имеет `field__input` (строка 182) — заработает сам.
   `.field__required` на span уже есть.
5. Шаговые заголовки (D-07): перед секцией CDEK/получателя добавить нумерованные caption/uppercase
   заголовки («Шаг 1. Получатель» / «Шаг 2. Доставка» — формулировки по §24; маппинг Cart = шаги 1–3).
   Стиль — как `checkout__section-title`, на токенах. Только визуально, без stepper-компонента.
6. Степпер количества (SHOULD): привести к PDP-паттерну 3-B (`ProductDetail.vue:79-111`):
   та же геометрия кнопок, aria-label «Уменьшить количество»/«Увеличить количество» на qty-btn.
   `data-testid` НЕ добавлять (E2E не завязан; `cart-item`/`cart-item-select` не трогаем).
   Логика clamp 1..stock уже есть в `:disabled`.

Style (scoped):

- Радиусы: 14px → `var(--radius-lg)`, 10px → `var(--radius-md)`, 12px → `var(--radius-lg)`
  (cart__count pill-образный — можно `--radius-pill`), 8px → `var(--radius-sm)`.
- Тень checkout-bar `0 4px 20px rgba(0,0,0,0.08)` → `var(--shadow-card)`.
- `rgba(0, 0, 0, 0.12)` (placeholder) → `var(--color-text-muted)`.
- `#fff0f0` (hover remove-desktop) → `color-mix(in srgb, var(--color-danger) 8%, transparent)`.
- `#cccccc` disabled checkout-btn → удалить (AppButton даёт `opacity: 0.5`); `#fff` → `var(--color-white)`.
- Типографика: 22px → `var(--font-size-h3)`, 15/14/13/12px → `--font-size-body/body-sm/caption` по месту;
  font-weight 500/600/700 → `--font-weight-medium/semibold/bold`.
- Поля получателя: удалить локальные стили `.cart__recipient-field input/select` (1205-1226) и
  `.cart__recipient-field label` — заменяются глобальными `.field*`; оставить grid-раскладку
  (`.cart__recipient-fields`, `--wide`).
- `.cart__recipient-error` — оставить общий блок ошибки, цвет `var(--color-error)` (spec Edge Cases:
  `.field__input--error` per-field не вводим, логику валидации не меняем).
- Удалить мёртвый CSS: `.cart__loading` + `@keyframes spin` (757-775; в шаблоне loading = SkeletonCartItem,
  класса нет), `.cart__summary-free` (1055-1058), `.cart__delivery-*` (1060-1112).
  **Предварительно проверено:** grep по `frontend/src` — `cart__delivery*` встречается только в
  Cart.vue, `CdekDeliveryWidget` эти классы НЕ использует.
- Удалить локальные `.cart__checkout-btn`, `.cart__recipient-new-button`, `.cart__empty-btn` стили
  (заменены AppButton).

Проверка: `npx vitest run src/__tests__/Cart.spec.js` в worktree + lint. Ручной осмотр diff на
сохранность всех testid: cart-page, cart-title, cart-select-all, cart-item, cart-item-select,
recipient-select, recipient-new-button, recipient-first-name/last-name/country-code/patronymic/phone,
checkout-button.

### Шаг 3. `frontend/src/views/Checkout.vue` — рестайл (D-06/07)

Template:

1. `pay-button` (67-75) → `<AppButton variant="primary" block :loading="processing" data-testid="pay-button" @click="processPayment">`
   со слотом «Оплатить … ₽ / Переход к оплате...» (текст на нашей стороне).
2. `checkout__cancel` (78-80) → `<AppButton variant="ghost" block :disabled="processing" @click="cancelPayment">Отменить</AppButton>`.
3. `checkout__retry` (16) → `<AppButton variant="primary" size="sm" @click="fetchOrder">Повторить</AppButton>`.
4. `checkout__back` — оставить нативной icon-кнопкой, стили на токены (radius `--radius-md`).
5. Шаговые заголовки (D-07): перед карточками — нумерованные заголовки секций (шаги 4–6 по §24:
   сводка/доставка/оплата), стиль `checkout__section-title` на токенах.

Style:

- Security-блок: `background: #e8f0fe; color: #1a73e8` → `var(--color-primary-light)` / `var(--color-primary)`.
- Карточки 16px → `var(--radius-lg)`; payment-method/security 10px → `var(--radius-md)`.
- Типографика на `--font-size-*` (28px amount → `--font-size-h2`, 13/14/15px → body-sm/caption и т.д.),
  веса на `--font-weight-*`.
- `#fff` → `var(--color-white)`; удалить `.checkout__pay-btn`/`.checkout__cancel`/`.checkout__retry` стили.
- Все `data-testid` сохранить: checkout-page, checkout-recipient, checkout-recipient-phone, pay-button.

Проверка: `npx vitest run src/__tests__/Checkout.spec.js` + lint.

### Шаг 4. Тесты и финальные гейты

1. `make -C "$WORKTREE" test-frontend` — полный vitest (≥439). Править только упавшее от смены
   разметки (ожидаемо: ничего или empty-state в Cart.spec.js, если тест ищет `cart__empty-btn`/`router-link` —
   grep таких не нашёл, но подтвердить прогоном).
2. `make -C "$WORKTREE" lint-frontend` — 0 errors / 0 warnings.
3. Grep-аудит изменённых файлов: ни одного `#[0-9a-fA-F]{3,6}` / `rgba(` вне `--color-*` определений
   (`--shadow-*` в base.css уже существуют — не трогаем).
4. `pytest` backend (644 passed) — гейт обязателен, затронут быть не должен.
5. E2E по возможности: `cart-select.spec.js`, `checkout.spec.js`, `checkout-failed-cards.spec.js`,
   visual-smoke 11/11 — ожидание: 117 passed + те же 3 известных падения (не чинить).
6. Self-review по ролевому файлу: полный diff vs spec Must-haves, 3–5 потенциальных проблем.

## 3. Risks / Open questions

- **AppButton vs unit-тесты на `disabled`:** AppButton ставит `:disabled="disabled || loading"` —
  тесты `checkout-button`/`pay-button` на `attributes('disabled')` совместимы. Риск низкий.
- **Смена тега в empty-state (router-link → button):** visual-smoke `/cart` рендерит пустую корзину —
  проверить 11/11. Если тест ищет `a[href="/"]` — поправить тест (только это место).
- **Глобальные `.field__input` vs scoped-копии в 11+ компонентах:** scoped CSS имеет приоритет над
  глобальным — существующие страницы не изменятся. Риск минимален; не рефакторим их (Out of Scope).
- **`.field__input` на `<select>`:** padding `0 var(--space-4)` + height 48px применимы к select;
  стрелка браузерная — приемлемо, визуально сверить.
- **Шаговые заголовки:** точные формулировки шагов (1–3 в Cart, 4–6 в Checkout) сверить с
  `docs/design/design-system-detailed.md` §24 при имплементации; никакого роутинга/валидации шагов.
- **color-mix поддержка:** `color-mix(in srgb, …)` для `#fff0f0`-замены — поддержка современных
  браузеров ок; fallback не нужен (hover-эффект). Если lint ругнётся — заменить на `--color-primary-light`-подобный подход с `--color-danger`-оттенком зафиксировать в PR.
- Открытых вопросов к пользователю нет: промо-блок (D-08) и error-стиль полей (общий блок) решены в spec.
