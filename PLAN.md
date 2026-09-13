# PLAN.md — design-header-pr209 (frontend-dev)

- **Спека:** `.agent/runs/design-header-pr209/spec.md` — ОДОБРЕНА (включая D-05: responsive.spec.js переписывается под §11 `[Menu][Logo][Cart]`).
- **Ветка:** `feature/design-header-pr209` · **Замок:** `frontend` · **Issue:** #250.

## 1. Goal

Привести Header к §11 дизайн-системы (desktop 72px + мобильная шапка `[Menu][Logo][Cart]` с drawer-меню и строкой поиска) и завершить миграцию оставшихся текстовых кнопок на `AppButton` (§10), не сломав testid-контракт D-04, sticky/toast-поведение и E2E-baseline.

## 2. Шаги (порядок из спеки §Parallelization Plan)

### Шаг 1. AppButton: prop `type` + variant `danger` (D-07, D-08)

Файлы: `frontend/src/components/ui/AppButton.vue`, `frontend/src/__tests__/AppButton.spec.js` (путь уточнить по факту — рядом с Header.spec.js в `src/__tests__/`).

- Добавить `type: { type: String, default: 'button' }` и `:type="type"` на корневой `<button>` (сейчас захардкожен `type="button"` — AppButton.vue:3).
- Добавить variant `danger` в validator + стили `.app-button--danger` (`background: var(--color-danger); color: var(--color-white)`; hover через `color-mix`, паттерн как в Header.vue:426).
- Unit-тесты: `type="submit"` прокидывается; `danger` добавляет класс.

**Проверка:** `make -C "$WORKTREE" test-frontend` (AppButton.spec зелёный), `make -C "$WORKTREE" lint-frontend`.

### Шаг 2. MobileMenuDrawer.vue + unit-тесты (D-02)

Файлы: новый `frontend/src/components/MobileMenuDrawer.vue`, новый `frontend/src/__tests__/MobileMenuDrawer.spec.js`.

- Props `open`, emits `close`; `data-testid="mobile-menu-drawer"`, `aria-label`, начальный focus на drawer (focus-trap — out of scope, issue #225).
- Пункты: Каталог (`/`); по `isAuthenticated` — Заказы (`/orders`), Уведомления (`/notifications`), Профиль; гостю — Войти (`/login`); по `isSupplier` — Дашборд/Мои товары/Мои заказы.
- Overlay-затемнение слева; закрытие по клику вне, Escape, выбору пункта; z-index 300 (выше header 100 и toast 200, D-10); токены `--color-bg-white`, `--shadow-dropdown`, `--radius-lg`. Новых токенов не вводить.
- Тесты: пункты по auth/supplier/guest; close по Escape и click-outside.

**Проверка:** vitest MobileMenuDrawer.spec зелёный, lint чистый.

### Шаг 3. Header.vue — мобильный блок + desktop-доработки (D-01, D-03, D-04, D-09)

Файл: `frontend/src/components/Header.vue`.

- Template: добавить `.header__mobile-top` (виден только <768px): `mobile-menu-btn` (burger, aria-label, touch target ≥44px), логотип (существующий `data-testid="header-logo"` — элемент остаётся ОДИН, визуально переносится), `mobile-cart-link` (router-link `/cart` с бейджем `cartCount`, тот же класс `.header__notif-badge`). Ниже `.header__mobile-search` с `SearchBar` и `data-testid="header-search-bar-mobile"`, горизонтальные паддинги 16px. Поведение mobile search overlay (#171) НЕ менять.
- Подключить `<MobileMenuDrawer :open="mobileMenuOpen" @close="mobileMenuOpen = false" />`; добавить `mobileMenuOpen` ref.
- Desktop (D-03): добавить ghost nav-link «Каталог» → `/` в `.header__nav`; сверить отступы с §11. Phone/Compare НЕ добавляем.
- **НЕ удалять и не переименовывать:** классы `.header`, `.header__actions`, `.header__icon`, `.header__toast`, `.header__notif-badge` (Header.spec.js читает исходник строками, `src/__tests__/Header.spec.js:9,79-96`); testid `header-logo`, `header-search-bar`, `cart-link`, `profile-link`, `login-link`, `notifications-btn`; `position: sticky; top: 0` (toast-follow-scroll.spec.js, 4 теста).
- **testid-контракт D-04 дословно:** сохраняются `header-logo`, `header-search-bar`, `cart-link`, `profile-link`, `login-link`, `notifications-btn`; новые `mobile-menu-btn`, `mobile-cart-link`, `mobile-menu-drawer`, `header-search-bar-mobile`. **НОЛЬ дублей testid** (Playwright strict mode): `cart-link` остаётся ТОЛЬКО в desktop `.header__actions`; мобильная корзина — отдельный `mobile-cart-link`. Desktop search — `header-search-bar`, мобильный — `header-search-bar-mobile`.
- Style: media 768px — `.header__mobile-top`/`.header__mobile-search` hidden на ≥768px; desktop search/actions hidden <768px (правило `@media (max-width: 767px)` + `.header__actions { display: none; }` сохранить дословно — его проверяет Header.spec.js:79-83). Desktop header 72px остаётся; мобильная высота auto (2 строки).
- Обновить `src/__tests__/Header.spec.js`: оставить source-string проверки, добавить рендер `mobile-menu-btn`/`mobile-cart-link`, бейдж на mobile cart при `cartCount=2`, открытие/закрытие drawer по клику.

**Проверка:** vitest Header/MobileMenuDrawer зелёные; `grep -o 'data-testid="[^"]*"' src/components/Header.vue | sort | uniq -d` — пусто (ноль дублей); lint чистый.

### Шаг 4. Миграция кнопок views на AppButton (D-06) — 4 логические группы

Механическая замена `<button class="X__btn">` → `<AppButton variant=... :type=...>`, сохраняя `data-testid`, `@click`, `:disabled`; удаление мёртвого CSS кнопок. `danger` — для logout/cancel/delete; `type="submit"` — в `<form>`; `admin__btn--success` → `primary`; CdekDeliveryWidget «Изменить» → `ghost`/`sm`.

- **4a. Auth-страницы:** `Login.vue`, `Register.vue` (submit; OAuth brand-кнопки ОСТАВЛЯЕМ), `ForgotPassword.vue`, `ResetPassword.vue`, `GuestCheckout.vue` (мёртвый код, мигрируем для консистентности).
- **4b. Профиль/заказы пользователя:** `Profile.vue` (retry + logout→danger; `.action-btn` router-link'и оставляем), `ProfileEdit.vue` (submit), `ProfileRecipients.vue` (add, empty-btn, modal submit), `Orders.vue` (retry + cancel→danger), `OrderDetail.vue` (retry + cancel→danger), `Notifications.vue` (mark-read-all), `PaymentFailed.vue` (2), `PaymentSuccess.vue` (2 `<button>`; `.payment-result__btn` router-link'и — НЕ кнопки, оставляем).
- **4c. Supplier:** `SupplierOrders.vue` (retry; items-toggle-раскрывашку оставляем), `SupplierProducts.vue` (add ×2, edit/delete карточки), `SupplierDashboard.vue` (1).
- **4d. Admin + прочее:** `Admin.vue` (add-category, add-delivery, user-action, modal submits), `admin/UserDetailsModal.vue`, `admin/AdminOrderModal.vue` (submit, success/cancel), `ProductFormModal.vue` (submit), `CdekDeliveryWidget.vue` («Изменить» → ghost/sm).
- **Осознанно оставляем (D-06):** icon-кнопки (back-arrow, `modal__close`, `field-toggle` eye, qty-степперы, `image-thumb__remove`, lightbox close, toast close, header icon-кнопки, SearchBar внутренние), чипы (CategoryChips, CategoryCard, SearchBar-теги, FilterPanel), `admin__icon-btn`, OAuth brand buttons, router-link'и под кнопки.
- Точечно править spec-файлы, если проверяют CSS-классы мигрированных кнопок.

**Проверка после каждой группы:** `make -C "$WORKTREE" test-frontend` зелёный. После всех групп: `grep -rn '<button' frontend/src/views frontend/src/components` — остались только категории «оставляем» из D-06; lint чистый.

### Шаг 5. E2E responsive.spec.js (D-05)

Файл: `frontend/e2e/responsive.spec.js`.

- Переписать тест «header shows only logo and hides action icons on mobile» (строки 57-66): мобильная шапка показывает `mobile-menu-btn`, `header-logo`, `mobile-cart-link`, `header-search-bar-mobile`; `.header__actions` по-прежнему hidden; desktop `cart-link`/`profile-link`/`login-link` hidden (они в `.header__actions`).
- Desktop-тест (строки 68-76) без изменений. Остальные блоки (horizontal scroll, bottom-nav badge) не трогаем.
- helpers.js: `goToCart`/`goToProfile` используют `cart-link`/`profile-link` с fallback на bottom-nav через `isVisible()` — на мобильном desktop-ссылки hidden, fallback работает, helpers НЕ правим.

**Проверка:** `make -C "$WORKTREE" test-e2e` — responsive.spec.js зелёный; baseline 117 passed + известные предсуществующие падения (auth:72, search-filter:82, checkout:152 флаки); toast-follow-scroll 4/4; visual-smoke 11/11.

### Шаг 6. Финальный self-review и отчёт

- `git -C "$WORKTREE" --no-pager diff origin/main...HEAD` — сопоставить каждый Must-have спеки с diff; adversarial audit по ролевому чеклисту (testid, console.log, scope creep).
- `make -C "$WORKTREE" test-frontend` + `lint-frontend` — зелёные.
- Коммит в feature-ветку (без push), обновить `docs/journal/session-log.md`.

## 3. Risks / Open questions

- **R-1: Header.spec.js читает исходник строками** (`readFileSync`, Header.spec.js:9) — проверяет `@media (max-width: 767px)`, `.header__actions {`, `display: none;`, `.header__icon {`, `position: relative;`. Эти строки сохранить дословно; новые media-правила добавлять рядом, не переписывая существующие.
- **R-2: Дубли testid → Playwright strict mode.** Мобильные элементы получают НОВЫЕ testid; `cart-link` только desktop. Проверка `uniq -d` на шаге 3.
- **R-3: z-index drawer (300) vs toast (200) и модалки** — smoke-проверка вручную на /profile/edit (спека Risks).
- **R-4: Крупный механический diff (~20 views)** — митигируется группировкой 4a–4d с прогоном тестов после каждой группы и чек-листом D-06 при self-review.
- **R-5: spec-файлы views могут проверять старые CSS-классы кнопок** — точечные правки в шаге 4, падения всплывут на vitest.
- **R-6: Drawer при resize до desktop** — скрывается CSS (mobile-блоки hidden ≥768px); состояние `mobileMenuOpen` сбрасывать не обязательно, но проверить визуально.
- **Open questions:** нет — D-05 подтверждён владельцем, скоуп D-06 исчерпывающий.
