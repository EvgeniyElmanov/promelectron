# PLAN: design-catalog-pdp-pr209 (issue #248)

**Роль:** frontend-dev · **Ветка:** `feature/design-catalog-pdp-pr209` · **Дата:** 2026-09-13

## 1. Goal

Рестайл страниц каталога (`Products.vue`, §21) и PDP (`ProductDetail.vue`, §20) на токенах и примитивах этапов 1–3A (AppBreadcrumbs, AppButton, токены `base.css`) без изменения бизнес-логики, API и существующих `data-testid`; критерий успеха — `make test-frontend` и `make lint-frontend` зелёные, E2E-baseline не хуже (117 passed + ≤3 известных падения).

## 2. Решённые открытые вопросы спеки (проверено до плана)

- **`category_name` в `/products/{id}/detail` — НЕТ.** `backend/src/app/schemas/product.py:69-75` (`ProductDetailOut`) содержит только `category_id` (строка 22). Значит по D-02 крошки PDP = `Главная / Каталог / <product.name>`, звено категории **не добавляем**, API не трогаем.
- **Catalog-крошки:** звено категории возможно только в search-режиме — `allCategories` грузится (`fetchAllCategories` вызывается только при `searchAvailable`, `Products.vue:379-381`) и даёт имя по `categoryId`. В legacy-режиме имени категории нет (`selectedCategory` — только id) → крошки всегда `Главная / Каталог`, звено категории добавляется только если имя найдено в `allCategories`.
- **AppButton** (`components/ui/AppButton.vue`) — `click` не объявлен в emits, нативный fallthrough работает (D-07); `data-testid`/`class`/`disabled` тоже проваливаются на `<button>`. Есть props `variant` (primary/secondary/ghost), `size` (md=48px/sm=40px), `loading`, `block`. Менять компонент не нужно.
- **Правило #171** — живёт в `base.css:128-133` (`@media (max-width:767px) { input,select,textarea { font-size: 16px !important } }`). Не трогаем; scoped-стили price-input (`font-size: 14px`) на мобилке ему проигрывают — при рестайле **не поднимать** font-size инпутов и не добавлять `!important`.
- **Токены на месте:** `--color-primary-light` (#e8f0fe-замена), `--color-danger` (#ff4242-замена), `--color-star` (#ffa800-замена для звёзд), `--color-success`, `--radius-lg/md`, `--space-*`. Новых токенов не потребуется.
- **`addToCart(productId, quantity = 1, product = null)`** (`useCart.js:56`) — сигнатура уже принимает qty; менять composable не нужно.
- **FilterPanel.vue** — уже на токенах, хардкод-цветов нет (проверено грепом); точечный рестайл не требуется, файл вне правок.

## 3. Steps

### Шаг 0. Подготовка
Проверить `git -C $WORKTREE status` — чисто; ветка `feature/design-catalog-pdp-pr209` актуальна от `origin/main` (merge/rebase при расхождении).

### Шаг 1. Products.vue — крошки + H1 (структура)
1. Импорт `AppBreadcrumbs` из `@/components/ui/AppBreadcrumbs.vue`.
2. `<AppBreadcrumbs :items="catalogCrumbs" />` в начало `.home__section` (над фильтрами).
3. `computed catalogCrumbs`: базово `[{label:'Главная',to:'/'},{label:'Каталог'}]`; если `searchAvailable` и `categoryId` и имя найдено в `allCategories` (плоский поиск по дереву, учесть вложенность `children`) — вставить `{label: <имя>}` перед последним элементом.
4. H1 «Каталог»: добавить `<h1 class="home__title">Каталог</h1>` рядом с крошками (визуально по §21). `h2[data-testid="products-section-title"]` **не трогаем** (D-04).
5. **Проверка:** `make -C $WORKTREE test-frontend` — Products.spec.js зелёный (дописать тест на крошки/H1, см. шаг 5).

### Шаг 2. Products.vue — рестайл фильтров/сортировки/состояний на токены
1. `sort-select`: высота 48px (§19), radius `var(--radius-md)`, border `var(--color-border)` — уже близко, привести; стрелку-шеврон в SVG-фоне перекрасить на `--color-text-secondary`-совместимый hex (SVG data-uri не читает var() — оставить hex, это не «хардкод-цвет UI», либо зафиксировать в PR).
2. `home__price-btn` → `AppButton` variant primary, size md (48px) или sm; `@click="applyFilters"` — нативный fallthrough (D-07). `data-testid="apply-price-btn"` сохранить дословно.
3. `home__load-more` → `AppButton` variant secondary, block; `:hover` с хардкодом `#e8f0fe` (Products.vue:634-636) удалить — hover уже в AppButton. `data-testid="load-more-btn"` сохранить.
4. Rating-кнопки: `--active` — `color: #fff` → `var(--color-white)`; border/pill-радиус 20px → `var(--radius-pill)` или оставить — по макету §21.
5. Empty-state `products-empty`: карточка `var(--color-bg-white)` + `var(--radius-lg)` + padding по токенам `--space-*`.
6. Сетка/grid, tabs, count — стили уже на токенах/нейтральны; только вычистить оставшиеся хардкоды в файле.
7. **Проверка:** `make -C $WORKTREE test-frontend` + `make -C $WORKTREE lint-frontend`.

### Шаг 3. ProductDetail.vue — крошки + AppButton + рестайл
1. Импорт `AppBreadcrumbs`; рендер первым элементом внутри `.product-detail` (над sticky-хедером — хедер sticky `top:0`, крошки над ним в потоке). Items: `[{label:'Главная',to:'/'},{label:'Каталог',to:'/'},{label: product.name}]` (категории нет — см. §2; «Каталог» ведёт на `/`, т.к. маршрута /catalog нет — D-01; допустимо сделать «Каталог» нелinkованным span, решить при реализации: AppBreadcrumbs делает ссылкой только не-последние items с `to`, последний всегда span).
2. `pdp-add-to-cart` → `AppButton` block, `:loading="cartLoading"`, `:disabled="isOutOfStock"`, `@click="addToCart"`; класс `--in-cart` сохранить (зелёное состояние `var(--color-success)`): AppButton принимает внешний class через fallthrough — либо оставить кастомный класс поверх, либо вариант через CSS. Текст/логика состояний (`В корзине · N`) без изменений. `data-testid="pdp-add-to-cart"` дословно.
3. `pdp-submit-review` → `AppButton` variant primary size md/sm. `data-testid="pdp-submit-review"` дословно.
4. Рестайл: `--fav-btn--active` `#ff4242` → `var(--color-danger)`; `--stock--out-of-stock` fallback убрать (`--color-danger` есть); звёзды `#FFB800`/`#ccc` → `var(--color-star)` / `var(--color-border)` (в SVG-атрибутах `fill`/`stroke` var() работает); радиусы 12px → `var(--radius-lg)` на галерее/секциях по §20; цена — размеры по §4 (28/32px уже близко).
5. Back-кнопка `pdp-back-button` и sticky-хедер — сохранить (D-08).
6. **Проверка:** vitest + lint; существующий тест на `--in-cart` класс должен пройти (класс сохранён).

### Шаг 4. ProductDetail.vue — quantity-stepper (D-05)
1. Инлайн-блок в `.product-detail__actions` рядом с кнопкой (без отдельного компонента — используется один раз): `ref qty = ref(1)`, кнопки `−`/`+` + `<input type="number">`, clamp `1..product.stock`; показывать только когда `!isOutOfStock && inCartQty === 0` (при in-cart кнопка ведёт в корзину — stepper бессмысленен).
2. `addToCart` → `addToCartStore(productId.value, qty.value, product.value)` (composable сам валидирует stock, `useCart.js:57`).
3. Новые testid (добавление не ломает E2E): `pdp-qty-decrease`, `pdp-qty-input`, `pdp-qty-increase`.
4. Input: font-size 16px на десктопе НЕ обязателен, но на мобилке сработает правило #171 из base.css — scoped-стиль не должен его перебивать `!important`.
5. **Проверка:** vitest + lint.

### Шаг 5. Unit-тесты
1. `Products.spec.js`: тест крошек (`app-breadcrumbs` виден, содержит «Каталог») и H1.
2. `ProductDetail.spec.js`: тест крошек (`Главная / Каталог / Test Product`); тесты quantity-stepper: дефолт 1, `+` до stock и не выше, `−` не ниже 1, add передаёт qty в корзину (`getQuantityInCart(1)` === qty после двух «+»).
3. Обновить существующие тесты, если обёртка AppButton меняет селекторы (селекторы по `data-testid` — не должны; тест на класс `--in-cart` проверить).
4. **Проверка:** `make -C $WORKTREE test-frontend` — весь suite зелёный (baseline 434 + новые).

### Шаг 6. Финальные прогоны и self-review
1. `make -C $WORKTREE lint-frontend` — 0 warnings/errors.
2. `make -C $WORKTREE test-frontend` — зелёный.
3. Adversarial self-review по `git diff origin/main...HEAD`: все testid дословно, нет `console.log`, нет прямых axios-вызовов, нет новых хардкод-цветов, правило #171 не нарушено, каждый Must-have спеки покрыт diff'ом.
4. E2E (`make test-e2e`) — фаза QA после dev; visual-smoke baseline-обновление при необходимости зафиксировать в отчёте.

## 4. Risks / Open questions

- **AppButton + внешние классы/стили:** `--in-cart` зелёный фон придётся давать поверх `app-button--primary` (специфичность scoped-стилей view vs ui-компонента — проверить, может понадобиться `:deep()` или класс-модификатор в самом AppButton; предпочесть внешний класс без правки AppButton).
- **Крошка «Каталог» на PDP ведёт на `/`** — тот же маршрут, что «Главная». Визуально корректно, но два звена на один маршрут; альтернатива — «Каталог» без `to` (span). Решение при реализации: сделать link на `/` (совпадает с поведением каталога на главной), отметить в отчёте.
- **Крошки в search-режиме каталога:** поиск имени категории по дереву `allCategories` (вложенность) — если структура плоская/древовидная, нужен рекурсивный поиск; при промахе крошки деградируют до `Главная / Каталог` без падений.
- **Stepper vs «В корзине · N»:** при скрытии stepper'а в in-cart состоянии layout прыгает — зарезервировать ширину или принять (минор).
- **SVG-шеврон sort-select** — data-uri не читает CSS-переменные; оставить hex `#666` (фиксирую в отчёте как осознанное исключение) либо заменить на inline-SVG. Решение: оставить data-uri, зафиксировать.
- **visual-smoke (11 страниц)** почти наверняка потребует обновления скриншот-базлайна — ожидаемо, фиксируется в PR (AC-4).
- **Известные падения E2E** (auth:72, search-filter:82, checkout:152) не чиним — baseline 117 passed.
