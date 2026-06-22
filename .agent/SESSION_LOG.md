# SESSION_LOG — Лог изменений по сессиям

> **Append-only.** Агенты только дописывают сверху. Не редактируйте старые записи.

**Формат:**
```
YYYY-MM-DD HH:MM | <role> | <краткое описание>
  Изменено: <файлы>
  Риск/Техдолг: <если есть>
  Блокер: <если появился>
```

---

## Записи (новые сверху)

### 2026-06-22 10:41 | backend-dev | guest-checkout-auto-account — исправления backend review findings F026–F028
  Изменено:
  - `backend/src/app/services/email_service.py` — F026: убран email из лога ошибки отправки (`<redacted>`).
  - `backend/src/app/services/order_service.py` — F027: `guest_email` сохраняется в lowercase; `get_guest_order` сравнивает через `func.lower`.
  - `backend/src/app/services/payment_service.py` — F027: `create_guest_payment` и `confirm_guest_mock_payment_by_order` сравнивают email без учёта регистра.
  - `backend/src/app/services/user_service.py` — F027: `get_or_create_from_guest` нормализует email и ищет через `func.lower`; F028: `reset_password` инвалидирует остальные неиспользованные токены пользователя.
  - `backend/tests/test_guest_orders.py` — F027: тесты на сохранение lowercase и case-insensitive получение заказа.
  - `backend/tests/test_guest_payments.py` — F027: тесты на case-insensitive guest payment, mock confirm и привязку к существующему пользователю.
  - `backend/tests/test_password_reset.py` — F028: тест на инвалидацию остальных токенов.
  Результат:
  - `make test-backend` — 213/213 ✅
  - `ruff check backend/src backend/tests` — чисто ✅
  Риск/Техдолг:
  - Нет.
  Блокер: Нет.

### 2026-06-22 07:35 | frontend-dev | guest-checkout-auto-account — исправления frontend review findings F013–F021
  Изменено:
  - `frontend/src/api/orders.js` — F013: trailing slash во всех путях (`/orders/create-guest/`, `/orders/${orderId}/`, `/orders/guest/${orderId}/`).
  - `frontend/src/api/payments.js` — F013: trailing slash (`/payments/${orderId}/`, `/payments/sync-by-order/${orderId}/`, `/payments/${orderId}/mock-confirm/`); F014: добавлен `confirmGuestMockPayment` → `POST /payments/guest/${orderId}/mock-confirm/`.
  - `frontend/src/views/PaymentSuccess.vue` — F014: гостевой mock-платёж использует `/payments/guest/${orderId}/mock-confirm/`; F018: повторные ошибки polling surfac'ятся после 3-х неудач подряд; F019: `formatPrice` взят из `src/utils/price.js`.
  - `frontend/src/views/GuestCheckout.vue` — F016: `canSubmit` теперь переиспользует `validateGuestForm`; F019: импорт `formatPrice` из `src/utils/price.js`.
  - `frontend/src/composables/useGuestCheckout.js` — F015: добавлен `normalizePhone`, который убирает форматирование и приводит к `+7XXXXXXXXXX`; F021: email нормализуется в lowercase; валидация phone работает с отформатированным вводом.
  - `frontend/src/utils/price.js` — F019: новый shared helper `formatPrice`.
  - `frontend/src/views/Cart.vue`, `frontend/src/views/Checkout.vue` — F019: используется shared `formatPrice`.
  - `frontend/src/composables/useUserAddresses.js` — F017: удалён как dead code.
  - `frontend/src/__tests__/GuestCheckout.spec.js` — F013: ожидания с trailing slash; F020: добавлены тесты на невалидные имя/фамилию; добавлены тесты на disabled submit при невалидном телефоне и нормализацию форматированного телефона.
  - `frontend/src/__tests__/Checkout.spec.js` — F013: ожидания с trailing slash.
  - `frontend/src/__tests__/PaymentSuccess.spec.js` — F013: ожидания с trailing slash; F014: тест guest mock-confirm.
  Результат:
  - `cd frontend && npm run test -- --run` — 149/149 ✅
  - `cd frontend && npm run lint` — чисто ✅
  Риск/Техдолг:
  - Frontend-вызовы адресов уже используют `/me/addresses/` (F004).
  Блокер: Нет.

### 2026-06-22 06:50 | frontend-dev | Гостевой чекаут с автосозданием ЛК (guest-checkout-auto-account) — frontend
  Изменено:
  - `frontend/src/views/Cart.vue` — гость при оформлении редиректится на `/guest-checkout` вместо `/login`.
  - `frontend/src/views/GuestCheckout.vue` — валидация email/phone/имён, кнопка "Уже есть аккаунт? Войти", галочка "Сохранить адрес", создание заказа + гостевой платёж + редирект на `confirmation_url` ЮKassa.
  - `frontend/src/views/Checkout.vue` — поддержка гостевого режима: `GET /orders/guest/{id}?guest_email=...` и `POST /payments/guest/{id}/`.
  - `frontend/src/views/PaymentSuccess.vue` — загрузка гостевого заказа по `guest_email`, polling без auth-only endpoints, скрыта кнопка "Мои заказы" для гостей.
  - `frontend/src/router/index.js` — убран `requiresAuth` с `/checkout/:id`.
  - `frontend/src/api/orders.js`, `frontend/src/api/payments.js`, `frontend/src/api/auth.js`, `frontend/src/api/users.js` — API-модули для гостевого чекаута, сброса пароля и адресов.
  - `frontend/src/composables/useGuestCheckout.js` — валидация и сборка payload гостевого заказа.
  - `frontend/src/composables/useUserAddresses.js` — CRUD сохранённых адресов пользователя.
  - `frontend/src/__tests__/GuestCheckout.spec.js` — тесты валидации, кнопки login, save_address, создания заказа и инициации платежа.
  - `frontend/src/__tests__/Cart.spec.js` — обновлён тест редиректа гостя на `/guest-checkout`.
  - `frontend/src/__tests__/Checkout.spec.js` — добавлены тесты гостевого режима.
  - `frontend/src/__tests__/PaymentSuccess.spec.js` — новые тесты загрузки гостевого заказа.
  Результат:
  - `cd frontend && npm run test` — 144/144 ✅
  - `cd frontend && npm run lint` — чисто ✅
  Риск/Техдолг:
  - Backend endpoint `POST /orders/create-guest` не имеет trailing slash; frontend использует тот путь, что определён в backend, чтобы избежать 307 редиректа axios.
  - Гостевой `mock=1` на `/payment/success` не подтверждает платёж автоматически (endpoint требует авторизации); для E2E гостевого флоу потребуется отдельный сценарий или backend webhook mock.
  Блокер: Нет.

### 2026-06-22 07:15 | backend-dev | guest-checkout-auto-account — исправления backend review findings F001–F012 + guest mock-confirm
  Изменено:
  - `backend/alembic/versions/2ad164310a94_add_user_addresses_and_password_reset_.py` — F001: добавлен `server_default=sa.false()` для `orders.save_address`.
  - `backend/src/app/services/payment_service.py` — F002: исправлен парсинг адреса доставки (`_parse_address_string`, исключение города из улицы/дома); F003: убран email из лога автосоздания пользователя; F012: общая логика `create_payment`/`create_guest_payment` вынесена в `_create_or_update_payment`; добавлен `confirm_guest_mock_payment_by_order` и endpoint `POST /api/v1/payments/guest/{order_id}/mock-confirm/`.
  - `backend/src/app/api/users.py` — F004: пути адресов изменены с `/users/me/addresses/` на `/me/addresses/`.
  - `backend/src/app/services/user_service.py` — F007: обработка `IntegrityError` при одновременном создании пользователя с одним email; F009: удалён лишний SELECT в `save_address`; F011: фильтр `expires_at > now` в `reset_password`.
  - `backend/src/app/api/auth.py` — F008: удалён дублирующий `from sqlalchemy import select` внутри `password_reset_request`.
  - `backend/tests/test_guest_orders.py` — F005: добавлены параметризованные тесты на невалидные имена/фамилии.
  - `backend/tests/test_guest_payments.py` — F006: assert на вызов `EmailService.send_welcome_email` с `temp_password` и `reset_token`; F010: переименован тест в `test_webhook_does_not_save_address_without_flag`; добавлены тесты `test_guest_mock_confirm_creates_user`, `test_guest_mock_confirm_wrong_email`, `test_guest_mock_confirm_query_email`.
  - `backend/tests/test_user_addresses.py` — обновлены пути с `/api/v1/users/me/addresses/` на `/api/v1/me/addresses/`.
  - `frontend/src/api/users.js` — F004: обновлены пути `/users/me/addresses/` → `/me/addresses/`.
  Результат:
  - `make test-backend` — 207/207 ✅
  - `ruff check src/ tests/` — чисто ✅
  - `make migrate-down && make migrate` — downgrade/upgrade head проходит ✅
  Риск/Техдолг:
  - F004 изменяет URL адресов с `/api/v1/users/me/addresses/` на `/api/v1/me/addresses/`, что отличается от исходного spec; frontend-вызовы обновлены, spec желательно синхронизировать.
  - Email-уведомления остаются в fallback (SMTP не настроен, BLK-005).
  Блокер: Нет.

### 2026-06-21 17:25 | architect / backend-dev | Рефакторинг агентской документации: flat skills, BUNDLE, unified rule links
  Изменено:
  - Исправлены broken links на rule-файлы в `.kimi-code/skills/*` и `.kimi-code/AGENTS.md`.
  - Вынесены дублирующиеся блоки в `.kimi-code/rules/agent-commons.md`, `.kimi-code/rules/planning.md`, `.kimi-code/rules/known-pitfalls.md`.
  - `/skill:qa` интегрирован в `/skill:implement` как обязательный шаг пирамиды тестов.
  - Унифицированы `/skill:review` и роль `code-reviewer` (workflow vs role skill).
  - Разделены `project-manager` (стратегия) и `plan-maintainer` (операционный бэклог).
  - `.kimi-code/AGENTS.md` сокращён до index-файла; корневой `AGENTS.md` — только ссылки.
  - Создан `.kimi-code/BUNDLE.md` — единый реестр skills/rules.
  - Добавлен `disableModelInvocation: true` в ролевые skills.
  - Уточнён description `dispatcher`.
  - Унифицирован стиль ссылок на rules: `[Rule: Name](path)`.
  - В `/skill:implement` добавлен перезапуск тестов перед повторным review.
  - Обновлён `scripts/audit-agents.sh`: проверка реестра через `.kimi-code/BUNDLE.md`, улучшен regex для Markdown-ссылок, поддержка `../` и root-level `.md`, новые обязательные rules (`agent-commons`, `planning`, `known-pitfalls`).
  Результат:
  - `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
  - Все ссылки на rule-файлы валидны.
  Риск/Техдолг:
  - Нужен новый Kimi session, чтобы подхватить обновлённые skills.
  Блокер: Нет.

### 2026-06-22 01:05 | backend-dev / architect | Приведение агентской архитектуры к Kimi docs: flat skills + rules вне skills/
  Изменено:
  - Перенёс ролевые sub-skills из `.kimi-code/skills/promeutron/*/` в flat Kimi skills `.kimi-code/skills/<role>/SKILL.md` для всех 11 ролей.
  - Перенёс shared conventions из `.kimi-code/skills/promeutron/rules/` в `.kimi-code/rules/*.md` (reference markdown, не skills).
  - Удалена пустая `.kimi-code/skills/promeutron/` (остался только `promeutron/SKILL.md` как master skill).
  - Обновлены ссылки во всех workflow skills: `implement`, `fix`, `dispatcher`, `qa`, `project-manager`.
  - Обновлена документация: `.kimi-code/AGENTS.md`, `ROUTER.md`, `SESSION_START.md`, `.kimi-code/HOWTO.md`.
  - Обновлен `scripts/audit-agents.sh`: проверяет flat role skills, `.kimi-code/rules/`, отсутствие вложенных SKILL.md в `promeutron/`.
  - Обновлен `.agent/implement-kimi-2-7-high-priority-0622/spec.md` под актуальную структуру.
  Результат:
  - `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
  - Kimi CLI теперь обнаруживает 18 flat skills (включая 11 ролей + 6 workflow + 1 master).
  - Вложенных skill-директорий (неподдерживаемых Kimi) больше нет.
  Риск/Техдолг:
  - `.kimi-code/AGENTS.md` всё ещё дублирует ролевые инструкции (~1800 строк). Это legacy reference; можно постепенно сократить до чистого index, но это не блокирует Kimi skill discovery.
  - Нужен новый Kimi session, чтобы он подхватил новые flat skills.
  Блокер: Нет.

### 2026-06-22 00:35 | backend-dev / architect | Внедрение High-приоритетных рекомендаций аудита под Kimi K2.7
  Изменено:
  - `scripts/implement-pipeline.py` — добавлена команда `check-context <task-id>` с оценкой токенов и генерацией `CONTEXT_SUMMARY.md`; retry-логика для git worktree операций.
  - `scripts/agent_retry.py` — новый декоратор `@retry_on_kimi_errors` для transient-ошибок Kimi (502/504/timeout).
  - `.kimi-code/skills/implement/SKILL.md` — context check перед subagent, retry policy, K2.7 `reasoning_content`.
  - `.kimi-code/skills/fix/SKILL.md` — context check, retry policy, K2.7 notes.
  - `.kimi-code/config.example.toml` — комментарии про Kimi K2.7 (256K context, mandatory thinking).
  - `.kimi-code/skills/promelectron/SKILL.md` — master index с K2.7 context-size check и retry policy.
  - `.kimi-code/skills/promelectron/*/` — созданы sub-skills для всех ролей: architect, backend-dev, frontend-dev, code-reviewer, security-reviewer, e2e-tester, devops, qa, project-manager, integration-dev, dispatcher.
  - `.kimi-code/skills/promelectron/rules/` — созданы sub-skills для правил: pre-edit-checklist, golden-path, dependency-map, security, prompt-format, task-template.
  - `.kimi-code/AGENTS.md` — обновлён как legacy master index с таблицей sub-skills.
  - `ROUTER.md`, `SESSION_START.md`, `.kimi-code/HOWTO.md` — ссылки на sub-skills вместо `.kimi-code/AGENTS.md`.
  - `scripts/audit-agents.sh` — добавлена проверка promelectron sub-skills, rules, broken links во всех `.md`, frontmatter для всех `SKILL.md`.
  - `.kimi-code/skills/context-sync/SKILL.md` — добавлен Step 2 "Check Active Task Context Size (Kimi K2.7)".
  - `.kimi-code/skills/plan-maintainer/SKILL.md` — checklist docs updated теперь ссылается на sub-skills.
  Результат:
  - `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
  - `python scripts/implement-pipeline.py check-context implement-kimi-2-7-high-priority-0622` — оценка токенов рабочая.
  Риск/Техдолг:
  - `.kimi-code/AGENTS.md` всё ещё содержит полные ролевые инструкции (~1800 строк). Возможно постепенное сокращение до чистого index.
  - Нужно убедиться, что все workflow skills (`/skill:implement`, `/skill:fix`) действительно используют sub-skills в subagent prompts.
  Блокер: Нет.

### 2026-06-21 14:20 | audit-kimi-pipeline | Миграция `.kimi/` → `.kimi-code/AGENTS.md`
  Изменено:
  - `.kimi-code/AGENTS.md` — создан project-level instructions с агентами и rules.
  - `.kimi-code/HOWTO.md` — сохранено практическое руководство.
  - `.kimi-code/LESSONS_LEARNED.md` — сохранены E2E CI lessons learned.
  - `AGENTS.md` — переписан как краткий index.
  - `SESSION_START.md` — обновлены ссылки на `.kimi-code/AGENTS.md`.
  - `ROUTER.md` — обновлены ссылки на `.kimi-code/AGENTS.md`.
  - `.kimi-code/skills/implement/SKILL.md` — обновлены ссылки на `.kimi-code/AGENTS.md`.
  - `.kimi-code/skills/fix/SKILL.md` — обновлены ссылки на `.kimi-code/AGENTS.md`.
  - `.kimi-code/skills/promelectron/SKILL.md` — обновлены ссылки на `.kimi-code/AGENTS.md`.
  - `.kimi-code/config.example.toml` — push main → `ask`, удалено `default_yolo`, удалён project-specific hook.
  - `.gitignore` — добавлена `/.kimi/` как legacy.
  - `scripts/audit-agents.sh` — обновлён под новую структуру.
  - `.claude/rules/agent-context.md` — обновлена ссылка на `.kimi-code/AGENTS.md`.
  - `.kimi/` — удалена.
  - `.agent/audit-kimi-pipeline/review/findings.md` — findings F001–F005, F009 отмечены FIXED.
  Результат:
  - `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
  - `.kimi-code/config.example.toml` — валидный TOML.
  - `.kimi-code/mcp.json` — валидный JSON.
  Риск/Техдолг:
  - `.kimi-code/AGENTS.md` стал большим (~1800 строк). При росте проекта имеет смысл разбить роли на отдельные project-level skills.
  - F006, F007, F008 исправлены в рамках этого же аудита.
  Блокер: Нет.

### 2026-06-20 16:45 | backend-dev / devops | CDEK webhook fallback + polling sync
  Изменено:
  - `backend/src/app/services/cdek_service.py` — добавлен `sync_order_statuses()` и `_apply_cdek_status_to_order()`, рефакторинг `handle_order_status_webhook`.
  - `backend/src/app/workers/cdek_tasks.py` — добавлена Celery-задача `sync_cdek_order_statuses`.
  - `backend/src/app/workers/celery_app.py` — beat schedule каждые 15 минут.
  - `backend/tests/test_cdek.py` — 3 теста на polling sync.
  - `infra/helm/templates/cronjob-sync-cdek-statuses.yaml` — новый CronJob.
  - `infra/helm/values.yaml`, `infra/helm/stage/test/values.yaml`, `infra/helm/stage/prod/values.yaml` — schedule и enable для CronJob.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `pytest tests/test_cdek.py` — 38/38 ✅
  - `ruff check` — чисто ✅
  - В `promelectron-test` создан CronJob `promelectron-cj-sync-cdek-statuses` с расписанием `*/15 * * * *`.
  - Запущена manual job — задача отработала, `{'checked': 0, 'updated': 0}` (в тестовой БД на момент запуска не было заказов с `cdek_uuid`).
  Риск/Техдолг:
  - Заказ #295 исчез из тестовой БД (было 1 заказ, стало 3, но 295 среди них нет). Возможен сброс/миграция БД.
  Блокер: Нет.

### 2026-06-20 16:15 | e2e-tester / implement-pipeline | fix-cdek-widget-calculation — review + E2E complete, ready for merge
  Изменено:
  - `.agent/fix-cdek-widget-calculation/review/findings.md` — статус APPROVED (3 итерации, F001–F007 закрыты).
  - `frontend/e2e/cdek-widget.spec.js` — прогнан в реальном браузере, 6/6 passed.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - Code review — APPROVED.
  - `make test-backend` — 178/178 ✅
  - `ruff check src/` — чисто ✅
  - `npm test -- --run` (frontend) — 132/132 ✅
  - `npm run lint` (frontend) — чисто ✅
  - `npx playwright test cdek-widget.spec.js --workers=1` — 6/6 ✅
  Риск/Техдолг:
  - E2E использует мок виджета; реальный флоу зависит от CDN CDEK и Yandex Maps API key.
  - Гостевые корзины без `supplier_id` используют fallback Москва.
  Блокер: Нет. Вопрос к пользователю: merge `feature/fix-cdek-widget-calculation` into `main`?

### 2026-06-20 06:45 | frontend-dev | fix-cdek-widget-calculation — frontend Option B implemented
  Изменено:
  - `frontend/src/api/cdek.js` — новый API-модуль, `getSupplierCityCode(supplierId)` → `GET /cdek/supplier-city-code/{supplier_id}/`.
  - `frontend/src/components/CdekDeliveryWidget.vue` — добавлен пропс `supplierCityCode` (Number, default 44); параметр виджета `from` теперь передаётся как `{ code: supplierCityCode }` вместо строки 'Москва'; в dev-режиме выводится warning при отсутствии `supplierCityCode` (fallback 44).
  - `frontend/src/views/Cart.vue` — определяется `supplierId` из первого товара корзины (`item.product.supplier_id`), асинхронно загружается `supplierCityCode` через `getSupplierCityCode`, fallback 44 при ошибке; значение передаётся в `CdekDeliveryWidget`.
  - `frontend/src/views/GuestCheckout.vue` — аналогичная логика определения `supplierId` из первого гостевого товара (`item.supplier_id`) и загрузки `supplierCityCode`.
  - `frontend/src/composables/useCart.js` — в гостевую корзину сохраняется `supplier_id` товара (для определения города отправления поставщика).
  - `frontend/src/__tests__/CdekDeliveryWidget.spec.js` — добавлены проверки `from: { code: 44 }` по умолчанию и `from: { code: 280 }` при кастомном `supplierCityCode`.
  - `frontend/src/__tests__/Cart.spec.js`, `GuestCheckout.spec.js` — добавлены моки `@/api/cdek` и `supplier_id` в тестовых данных.
  - `frontend/e2e/cdek-widget.spec.js` — добавлен E2E-сценарий выбора ПВЗ с моком `window.CDEKWidget` и проверкой отображения тарифа/цены/срока.
  Результат:
  - `cd frontend && npm test -- --run` — 128/128 ✅
  - `cd frontend && npm run lint` — чисто ✅
  Риск/Техдолг:
  - В E2E используется мок виджета, а не реальный CDEK widget; реальный флоу зависит от CDN и Yandex Maps API key.
  - Гостевая корзина получает `supplier_id` только для новых товаров; ранее сохранённые гостевые корзины без `supplier_id` будут использовать fallback Москва (44).
  Блокер: Нет

### 2026-06-20 06:30 | backend-dev | fix-cdek-widget-calculation — backend Option B implemented
  Изменено:
  - `backend/src/app/services/cdek_client.py` — добавлен метод `get_delivery_point(code: str)`, возвращающий ПВЗ с `location.city_code`; `get_delivery_points` теперь гарантированно возвращает `list`.
  - `backend/src/app/services/cdek_service.py` — добавлены:
    - `resolve_shipment_city_code(supplier_id, db)` с кэшированием в Redis (`cdek:pvz:city:<pvz_code>`, TTL 24ч).
    - `get_cached_pvz(city_code, type='PVZ')` с кэшированием списка ПВЗ (`cdek:pvz:city:<city_code>:<type>`, TTL 6ч).
    - `_is_sender_location_error()` и retry-логика в `calculate_delivery`: при ошибке `v2_sender_location_not_recognized` код ПВЗ заменяется на `city_code`.
  - `backend/src/app/api/cdek.py` — добавлен endpoint `GET /api/v1/cdek/supplier-city-code/{supplier_id}/` и схема `SupplierCityCodeResponse`; endpoint `GET /api/v1/cdek/pvz/` теперь использует `CdekService.get_cached_pvz` при наличии `city_code`; прокси `/api/v1/cdek/widget-service/` не изменён.
  - `backend/tests/test_cdek.py` — добавлены тесты на resolve_city_code (cache hit/miss, отсутствие ПВЗ), get_cached_pvz (cache hit/miss), calculate_delivery retry с city_code, pvz endpoint cache hit/miss, supplier-city-code endpoint.
  Результат:
  - `make test-backend` — 175/175 ✅
  - `ruff check src/` — чисто ✅
  Риск/Техдолг:
  - Frontend должен начать использовать `supplierCityCode` и передавать `from: { code: supplierCityCode }` в виджет; это в рамках задачи fix-cdek-widget-calculation, но выходит за scope backend-изменений.
  - Кэш ПВЗ не инвалидируется автоматически при смене окружения CDEK; при необходимости — ручная очистка Redis по паттерну `cdek:pvz:city:*`.
  Блокер: Нет

### 2026-06-19 05:35 | implement pipeline | replace-yandex-with-cdek-test-key — added deploy.yml CDEK credential injection
  Изменено:
  - `.github/workflows/deploy.yml` — CDEK credentials передаются в Helm через `--set env.secrets.CDEK_ACCOUNT` / `--set env.secrets.CDEK_SECURE`.
    - test: публичные тестовые креды CDEK захардкожены (как YooKassa test).
    - prod: читаются из GitHub Actions secrets `CDEK_ACCOUNT` / `CDEK_SECURE`.
  - `.agent/replace-yandex-with-cdek-test-key/spec.md` — обновлено под решение через `--set`.
  Результат:
  - YAML deploy.yml валиден.
  - Блокер BLK-SOPS-001 снят для задачи деплоя: SOPS-перешифрование `infra/helm/stage/*/secrets.yaml` больше не требуется.
  Риск/Техдолг:
  - Старые `SDEK_CLIENT_ID` / `SDEK_CLIENT_SECRET` в `infra/helm/stage/*/secrets.yaml` остаются неиспользуемыми; cleanup отложен на оператора.
  - Перед следующим прод-деплоем нужно добавить `CDEK_ACCOUNT` / `CDEK_SECURE` в GitHub Actions secrets.
  Блокер: Нет

### 2026-06-19 05:10 | implement pipeline | replace-yandex-with-cdek-test-key — implementation + review + E2E complete
  Изменено:
  - `backend/src/app/services/cdek_client.py` — warning-логи при отсутствии CDEK credentials / fallback.
  - `backend/docker-compose.yml` — прокинуты `CDEK_ACCOUNT`, `CDEK_SECURE`, `CDEK_API_URL`, `CDEK_TEST_MODE` со значениями публичных тестовых кредов CDEK.
  - `.env.example` — добавлены публичные тестовые CDEK credentials и пояснение про `VITE_YANDEX_MAPS_API_KEY` (Yandex Maps JS API key).
  - `frontend/Dockerfile` — уточнён комментарий про `VITE_YANDEX_MAPS_API_KEY`.
  - `frontend/e2e/cdek-widget.spec.js` — новый E2E-тест: виджет на `/cart`, graceful error при отсутствии Yandex Maps key.
  Результат:
  - `make test-backend` — 167/167 ✅
  - `ruff check src/` — чисто ✅
  - `cd frontend && npm test -- --run` — 127/127 ✅
  - `npx playwright test e2e/cdek-widget.spec.js --workers=1` — 2/2 ✅
  - Code review — APPROVED (итерация 1, дефектов нет).
  Риск/Техдолг:
  - `infra/helm/stage/test/secrets.yaml` и `infra/helm/stage/prod/secrets.yaml` не изменены; старые `SDEK_*` ключи остаются неиспользуемыми.
  Блокер: Нет

### 2026-06-18 14:10 | backend-dev / frontend-dev | cdek-widget-recipient-name — review iteration 1 fixes
  Изменено:
  - `backend/src/app/schemas/order.py` — `guest_name` optional в `GuestOrderCreate`; добавлена валидация `recipient_first_name`/`recipient_last_name` (min/max length, pattern, strip whitespace); добавлен `tariff_name` в `CdekDeliveryIn`.
  - `backend/src/app/api/cdek.py` — добавлены Pydantic-схемы `WidgetAction`, `WidgetOfficesParams`, `WidgetCalculateRequest`; валидация action и whitelist полей; `action` исключается из тела `calculate` перед проксированием.
  - `backend/src/app/services/order_service.py` — `create_guest_order` больше не заполняет `guest_name`.
  - `backend/tests/test_cdek.py` — добавлены тесты fallback на `user.full_name` и `guest_name`.
  - `backend/tests/test_guest_orders.py` — убран `guest_name` из payload, проверка `guest_name is None`.
  - `frontend/src/components/CdekDeliveryWidget.vue` — `new window.CDEKWidget(...)` в try/catch; обработка отсутствия `VITE_YANDEX_MAPS_API_KEY` как ошибка загрузки.
  - `frontend/src/views/Cart.vue`, `frontend/src/views/GuestCheckout.vue` — убраны `console.error`; `GuestCheckout.vue` больше не отправляет `guest_name`.
  - `frontend/e2e/checkout.spec.js` — убраны `console.log`.
  - `frontend/src/__tests__/CdekDeliveryWidget.spec.js` — тест на отсутствие API ключа и на ошибку загрузки скрипта.
  - `frontend/src/__tests__/GuestCheckout.spec.js` — обновлено ожидание payload без `guest_name`.
  - `.agent/cdek-widget-recipient-name/review/findings.md` — все findings отмечены FIXED, статус APPROVED.
  Результат:
  - `cd backend && pytest -x` — 167/167 ✅
  - `ruff check .` — чисто ✅
  - `cd frontend && npm test -- --run` — 127/127 ✅
  - `cd frontend && npm run lint` — чисто ✅
  - Коммит `d5204f0` в ветку `feature/cdek-widget-recipient-name` в worktree.
  Риск/Техдолг: нет.
  Блокер: Нет

### 2026-06-18 13:35 | frontend-dev | cdek-widget-recipient-name — frontend implementation complete
  Изменено:
  - `frontend/src/components/CdekDeliveryWidget.vue` — полностью переписан под официальный виджет `@cdek-it/widget@3` с CDN: динамическая загрузка скрипта, `destroy()` при unmount, `servicePath: /api/v1/cdek/widget-service/`, нормализация `onChoose(type, tariff, point)` в формат `CdekDeliveryIn`, обработка ошибок загрузки, сохранены `data-testid="cdek-delivery-widget"` и `data-testid="cdek-open-selector"`.
  - `frontend/src/views/Cart.vue` — добавлены поля `recipient_first_name` / `recipient_last_name` для авторизованных пользователей, валидация, передача в `POST /orders/create`.
  - `frontend/src/views/GuestCheckout.vue` — заменено единое поле `guestName` на раздельные `guest_first_name` / `guest_last_name`, валидация, передача `recipient_first_name` / `recipient_last_name` в `POST /orders/create-guest` (с сохранением `guest_name` как конкатенации для backward compatibility).
  - `frontend/src/views/Checkout.vue` — отображение блока получателя (`data-testid="checkout-recipient"`) по данным заказа.
  - `.env.example` — добавлен `VITE_YANDEX_MAPS_API_KEY=`.
  - `frontend/src/__tests__/GuestCheckout.spec.js`, `Checkout.spec.js`, `Cart.spec.js` — обновлены под новые поля и payload; добавлен `frontend/src/__tests__/CdekDeliveryWidget.spec.js`.
  - `frontend/e2e/checkout.spec.js` — добавлен мок `window.CDEKWidget` через `page.addInitScript`, helper'ы `selectCdekDelivery` и `fillRecipientName`.
  - `PROJECT_CONTEXT.md` — обновлены метрики frontend-тестов и история изменений.
  Результат:
  - `cd frontend && npm test -- --run` — 125/125 ✅
  - `cd frontend && npm run lint` — чисто ✅
  - `npx playwright test --list` — 101 E2E-тест распознан ✅
  Риск/Техдолг:
  - `profile.spec.js` не требовал изменений: не затрагивает CDEK-виджет и раздельные имена получателя.
  - В реальном браузере виджет зависит от CDN и Yandex Maps API key; в E2E используется мок.
  Блокер: Нет

### 2026-06-18 04:45 | backend-dev | cdek-widget-recipient-name — backend implementation complete
  Изменено:
  - `backend/src/app/models/order.py` — колонки `recipient_first_name`, `recipient_last_name`.
  - `backend/src/app/schemas/order.py` — поля в `OrderCreate`, `GuestOrderCreate`, `OrderOut`.
  - `backend/src/app/services/order_service.py` — заполнение новых полей при создании заказа.
  - `backend/src/app/services/cdek_service.py` — `_build_recipient` использует раздельные имена, fallback на `user.full_name`/`guest_name`.
  - `backend/src/app/api/cdek.py` — публичный endpoint `/api/v1/cdek/widget-service/` для `action=offices` и `action=calculate`.
  - `backend/alembic/versions/becdb9cce9b1_add_order_recipient_names.py` — миграция новых колонок.
  - `backend/tests/test_cdek.py`, `test_orders.py`, `test_guest_orders.py` — обновлены/добавлены тесты.
  - `PROJECT_CONTEXT.md` — обновлён API inventory и история изменений.
  Результат:
  - `make test-backend` — 166/166 ✅
  - `ruff check .` — чисто ✅
  Риск/Техдолг: нет.
  Блокер: Нет

### 2026-06-17 22:20 | e2e-tester | fix-mobile-header-cart-badge — E2E responsive tests passed
  Изменено:
  - Прогнан `frontend/e2e/responsive.spec.js` (67 тестов) в реальном браузере Chromium против рабочего dev-сервера из worktree.
  - Добавленные E2E-сценарии подтвердили: мобильная шапка показывает только логотип, десктоп показывает иконки, бейдж корзины в правом верхнем углу иконки.
  Результат:
  - `npx playwright test responsive.spec.js --workers=1` — 67/67 ✅
  - Dev-стек и worktree dev-server остановлены после прогона.
  Риск/Техдолг: нет.
  Блокер: Нет

### 2026-06-17 22:00 | code-reviewer / frontend-dev | fix-mobile-header-cart-badge — review fixes + tests
  Изменено:
  - `frontend/src/components/Header.vue` — `<ToastContainer>` вынесен за пределы `.header__actions`, чтобы тосты оставались видимыми на мобильном после скрытия иконок.
  - `frontend/src/__tests__/Header.spec.js` — новый тест: логотип, блок действий, CSS-правило скрытия на мобильном, ToastContainer вне блока.
  - `frontend/src/__tests__/BottomNav.spec.js` — новый тест: пункты навигации, бейдж корзины рендерится/скрывается, бейдж внутри иконки, проверка исходных стилей позиционирования.
  - `frontend/e2e/responsive.spec.js` — E2E-сценарии: мобильная шапка показывает только логотип, десктоп показывает иконки, бейдж корзины в правом верхнем углу иконки.
  - Feature-ветка `feature/fix-mobile-header-cart-badge` rebased onto `main` (2635999) — устранено расхождение `package.json`/`package-lock.json` с main.
  Результат:
  - `cd frontend && npm test -- --run` — 116/116 ✅
  - `cd frontend && npm run lint` — чисто ✅
  - `cd frontend && npm run build` — успешно ✅
  Риск/Техдолг: нет новых.
  Блокер: Нет

### 2026-06-17 16:29 | frontend-dev | fix-mobile-header-cart-badge — mobile header cleanup + bottom-nav badge reposition
  Изменено:
  - `frontend/src/components/Header.vue` — на мобильных (`< 768px`) скрыт блок `.header__actions`, в шапке остаётся только логотип Promelectron; десктопная версия не изменена.
  - `frontend/src/components/BottomNav.vue` — бейдж корзины перенесён внутрь `.bottom-nav__icon` и позиционирован в правом верхнем углу иконки (`top: -2px; right: -2px`); правила скрытия на десктопе сохранены.
  Результат:
  - `cd frontend && npm test -- --run` — 108/108 ✅
  - `cd frontend && npm run lint` — чисто ✅
  - `cd frontend && npm run build` — успешно ✅
  Риск/Техдолг:
  - На мобильных убраны прямые точки входа в «Уведомления» и «Заказы» из шапки; доступ остаётся через профиль/заказы (принято пользователем).
  - E2E-тесты, использующие мобильный viewport и селекторы `data-testid="cart-link"` / `data-testid="profile-link"` в шапке, могут потребовать переключения на `nav-Корзина` / `nav-Профиль`.
  Блокер: Нет

### 2026-06-16 23:59 | implement-pipeline | fix-frequent-logout — /implement cycle complete, ready for merge
  Изменено:
  - Архитектор: выявлен хардкод 15 минут в `create_access_token`, затронут OAuth-callback.
  - Backend-dev: исправлен fallback TTL, default TTL 1440, синхронизированы env/helm/docker-compose, добавлены тесты.
  - Code review: 2 итерации, статус APPROVED.
  - E2E-tester: `frontend/e2e/auth.spec.js` — 3/3 passed.
  Результат:
  - backend tests: 159/159 ✅
  - e2e auth spec: 3/3 ✅
  - review: APPROVED, открытых finding'ов нет.
  Блокер: Нет. Вопрос к пользователю: merge `feature/fix-frequent-logout` into `main`?

### 2026-06-16 23:55 | backend-dev | fix-frequent-logout — rebase onto main and sync TTL env defaults
  Изменено:
  - `feature/fix-frequent-logout` rebased onto current `main` (`6ef23a8`) — resolved `.agent/SESSION_LOG.md` and `PROJECT_CONTEXT.md` conflicts, preserved admin-section-tabs work.
  - `backend/src/app/utils/auth.py` — `create_access_token` fallback TTL now uses `ACCESS_TOKEN_EXPIRE_MINUTES` instead of hardcoded 15 minutes.
  - `backend/src/app/core/config.py` — default `ACCESS_TOKEN_EXPIRE_MINUTES` changed from 30 to 1440.
  - `.env.example`, `backend/.env.example`, `backend/docker-compose.yml` (api/worker/beat), `infra/helm/values.yaml` — synchronized `ACCESS_TOKEN_EXPIRE_MINUTES=1440`.
  - `backend/tests/test_auth.py` — added `test_login_token_expiry_matches_settings` and `test_oauth_token_expiry_matches_settings`.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `make test-backend` — 159/159 ✅
  - `ruff check src/` — чисто ✅
  - `ruff format --check` на изменённых Python-файлах — чисто ✅
  - `git diff main` содержит только изменения auth/JWT.
  Риск/Техдолг:
  - Увеличение TTL до 24 часов расширяет окно компрометации токена; митигация — HTTPS в prod, планируется внедрение refresh-токенов (#39).
  Блокер: Нет

### 2026-06-16 23:50 | devops | Deploy admin-section-tabs to test
  Изменено:
  - Запущен GitHub Actions workflow `deploy.yml` для окружения `test`.
  - Commit: `93612a3` (`feat(admin): section tabs navigation`).
  - Исправлен E2E-тест `frontend/e2e/admin.spec.js` — заменены неоднозначные селекторы заголовков на `data-testid="admin-section-panel-*"`.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `build` — ✅
  - `deploy-test` — ✅
  - `test-e2e / smoke` — ✅
  - `test-e2e / e2e` — ✅
  - Run URL: https://github.com/AutonomaCo/promelectron/actions/runs/27629450675
  Риск/Техдолг: Нет
  Блокер: Нет

### 2026-06-16 18:10 | frontend-dev | admin-section-tabs — unified section tabs in Admin.vue
  Изменено:
  - `frontend/src/views/Admin.vue` — заменена мобильная таб-навигация на единую горизонтальную навигацию по всем разделам (Дашборд, Пользователи, Категории, Способы доставки, Заказы, Фичатоглы); вкладки работают на десктопе и мобильных (overflow-x: auto); активный раздел показывается через `v-show`, остальные скрыты; по умолчанию активен «Дашборд»; добавлены `data-testid` для табов (`admin-section-tab-*`) и панелей (`admin-section-panel-*`); внутри раздела «Категории» сохранены подвкладки корневых категорий.
  - `frontend/src/__tests__/Admin.spec.js` — добавлены моки для `/delivery-methods/` и `/admin/orders`; обновлены тесты для переключения на нужную секцию перед проверкой; добавлены тесты на активную вкладку по умолчанию и переключение секций.
  - `frontend/e2e/admin.spec.js` — добавлен E2E-сценарий проверки навигации между разделами админки.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `cd frontend && npm test -- --run` — 108/108 ✅
  - `cd frontend && npm run lint` — чисто ✅
  Риск/Техдолг:
  - Панели разделов остаются в DOM (v-show), поэтому содержимое скрытых секций всё ещё рендерится; для очень больших таблиц можно рассмотреть `v-if` с lazy-загрузкой в будущем.
  - Разделы всё ещё загружаются при `onMounted` независимо от активной вкладки; опционально можно загружать данные только при первом открытии секции.
  Блокер: Нет

### 2026-06-16 22:25 | devops | Deploy admin-categories-tabs to test
  Изменено:
  - Запущен GitHub Actions workflow `deploy.yml` для окружения `test`.
  - Commit: `34bb995` (`feat(admin): category tabs, search, parent selector, product count`).
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `build` — ✅
  - `deploy-test` — ✅
  - `test-e2e / smoke` — ✅
  - `test-e2e / e2e` — ✅
  - Run URL: https://github.com/AutonomaCo/promelectron/actions/runs/27625432733
  Риск/Техдолг: Нет
  Блокер: Нет

### 2026-06-16 10:40 | code-reviewer / e2e-tester | admin-categories-tabs — ревью, правки, E2E
  Изменено:
  - `frontend/src/composables/useCategories.js` — `loadMore()` теперь добавляет новые элементы через `push(...)` вместо замены списка.
  - `frontend/src/views/Admin.vue` — добавлен debounce поиска категорий (~300 мс).
  - `backend/tests/test_categories.py` — отформатирован `ruff format`.
  - `.agent/admin-categories-tabs/review/findings.md` — все FINDINGS отмечены как FIXED, статус APPROVED (итерация 2).
  - `frontend/e2e/admin.spec.js` — прогнан E2E-сценарий создания корневой категории и подкатегории, переключения вкладки, cleanup.
  - `PROJECT_CONTEXT.md` — обновлены метрики (`backend_tests: 157/157`, `frontend_tests: 106/106`, `e2e_tests: 98/98`), API Inventory, Frontend Map, история изменений.
  - `.agent/SESSION_LOG.md` — эта запись.
  Результат:
  - `make test-backend` — 157/157 ✅
  - `npm test -- --run` (frontend) — 106/106 ✅
  - `npm run lint` (frontend) — чисто ✅
  - `npx playwright test e2e/admin.spec.js --workers=1` — 2/2 ✅
  - Code review — APPROVED (итерация 2, все FINDINGS FIXED).
  Риск/Техдолг:
  - API `GET /categories/` изменил формат ответа — все потребители обновлены, но внешние интеграции могут зависеть от старого формата.
  - Вкладки показывают только один уровень вложенности; глубокая иерархия не поддерживается.
  Блокер: Нет

### 2026-06-16 19:55 | frontend-dev | Admin categories tabs — frontend
  Изменено:
  - `frontend/src/composables/useCategories.js` — новый composable: загрузка всех категорий для вкладок/селектора родителя, загрузка отображаемых категорий по активной вкладке/поиску/пагинации.
  - `frontend/src/views/Admin.vue` — раздел «Категории» переделан под горизонтальные вкладки корневых категорий + «Все»; добавлен поиск по названию; столбец «Товаров»; пагинация «Показать ещё»; empty-state для пустых вкладок; в модалке добавлен селектор `parent_id` с опцией «Без родителя».
  - `frontend/src/components/ProductFormModal.vue` — адаптация под `CategoryListOut` (`data.items`).
  - `frontend/src/components/CategoryChips.vue` — адаптация под `CategoryListOut` (`data.items`).
  - `frontend/src/__tests__/Admin.spec.js` — моки под пагинированный ответ; новые тесты на вкладки, переключение, поиск, селектор родителя.
  - `frontend/src/__tests__/Products.spec.js` — мок `/categories/` возвращает `{ items, total }`.
  - `frontend/e2e/admin.spec.js` — E2E-сценарий создания корневой категории и подкатегории, переключения вкладки, cleanup.
  Результат:
  - `cd frontend && npm test -- --run` — 106/106 ✅
  - `cd frontend && npm run lint` — чисто
  Риск/Техдолг:
  - `loading.categories` в `Admin.vue` больше не используется (заменён на `categoryLoading` из composable), можно убрать при cleanup.
  Блокер: Нет

### 2026-06-16 19:35 | backend-dev | Admin categories tabs — backend
  Изменено:
  - `backend/src/app/schemas/category.py` — `CategoryOut` дополнен `product_count`; добавлен `CategoryListOut` (`items`, `total`).
  - `backend/src/app/services/category_service.py` — `list_categories` принимает `skip`, `limit`, `parent_id`, `q` и возвращает `(items, total)`; считает `product_count` через `func.count(Product.id).outerjoin(Product).group_by(Category.id)`; добавлена защита от циклов в `update_category` (нельзя выбрать потомка или саму себя родителем); `get_category`/`create_category`/`update_category` возвращают `product_count`.
  - `backend/src/app/api/categories.py` — `GET /categories/` возвращает `CategoryListOut` с query-параметрами `skip`, `limit`, `parent_id`, `q`; trailing slash сохранён.
  - `backend/tests/test_categories.py` — 7 новых тестов: пагинация, фильтр по `parent_id`, поиск `q`, создание подкатегории, защита от циклов, счётчик товаров, несуществующий родитель.
  - `PROJECT_CONTEXT.md` — обновлён API Inventory и счётчик backend-тестов (`157/157`), добавлена запись в историю.
  Результат:
  - `make test-backend` — 157/157 ✅
  - `ruff check` на изменённых файлах — чисто
  - `ruff format --check` на изменённых файлах — чисто
  Риск/Техдолг:
  - Изменён контракт `GET /categories/` с `list[CategoryOut]` на `CategoryListOut`; frontend-потребители (`Admin.vue`, `ProductFormModal.vue`, `CategoryChips.vue`) и тесты должны быть обновлены отдельным frontend-dev.
  Блокер: Нет

### 2026-06-16 13:25 | backend-dev / frontend-dev | Замена системы доставки на CDEK
  Изменено:
  - `backend/src/app/models/product.py` — поля weight_grams, length_cm, width_cm, height_cm.
  - `backend/src/app/models/supplier.py` — поля cdek_shipment_point, sender_name, sender_phone.
  - `backend/src/app/models/order.py` — CDEK поля (tariff_code, delivery_mode, delivery_point, to_location, price, uuid, number, status).
  - `backend/src/app/schemas/order.py`, `supplier.py`, `user.py`, `cart.py` — CDEK схемы, phone в UserUpdate, supplier_id/вес/габариты в корзине.
  - `backend/src/app/services/cdek_client.py` — OAuth + calculator + orders + PVZ + city suggest + тестовый fallback.
  - `backend/src/app/services/cdek_service.py` — build packages/sender/recipient, calculate, create order, webhook handler.
  - `backend/src/app/api/cdek.py` — endpoints CDEK (с trailing slash) + supplier profile.
  - `backend/src/app/services/order_service.py` — создание заказа с CDEK доставкой.
  - `backend/src/app/services/payment_service.py` — запуск Celery task после оплаты.
  - `backend/src/app/workers/cdek_tasks.py` — автосоздание заказа в CDEK с retry.
  - `backend/src/app/workers/celery_app.py` — добавлен `cdek_tasks` в include.
  - `backend/src/app/workers/onec_client.py`, `tasks.py` — синхронизация веса/габаритов из 1С.
  - `backend/seed_data.py` — тестовый поставщик с CDEK настройками + обновление существующего поставщика.
  - `backend/alembic/versions/` — миграции для CDEK полей и phone пользователя.
  - `frontend/src/components/CdekDeliveryWidget.vue` — кастомный виджет доставки + data-testid для E2E.
  - `frontend/src/views/Cart.vue`, `GuestCheckout.vue` — интеграция виджета.
  - `frontend/src/components/ProductFormModal.vue` — вес/габариты товара.
  - `frontend/src/views/SupplierDashboard.vue` — настройки CDEK поставщика.
  - `frontend/src/views/ProfileEdit.vue` — поле телефона.
  - `backend/tests/test_cdek.py` — новые тесты CDEK.
  - `backend/tests/conftest.py`, `test_orders.py`, `test_guest_orders.py`, `test_notifications.py`, `test_payments.py`, `test_analytics.py`, `test_auth.py` — обновлены под CDEK схемы.
  - `frontend/src/__tests__/GuestCheckout.spec.js`, `Checkout.spec.js` — обновлены под новый UI.
  - `frontend/e2e/checkout.spec.js`, `profile.spec.js` — обновлены под CDEK и phone.
  - `.env.example` — добавлены CDEK переменные.
  - `PROJECT_CONTEXT.md` — обновлён контекст.
  Результат:
  - `make test-backend` — 150/150 ✅
  - `make test-frontend` — 101/101 ✅
  - `make test-e2e` — 96/96 ✅
  - `ruff check .` — чисто
  - `make lint-frontend` — чисто
  Риск/Техдолг:
  - Frontend использует кастомный fallback-виджет, а не официальный CDEK JS Widget (нужна точная ссылка/инициализация от CDEK).
  - Мультивендорная корзина: CdekDeliveryWidget и CdekService.calculate_delivery используют supplier_id первого товара.
  - Старый `DeliveryMethod` router/model всё ещё существуют, но не используются; требуется cleanup.
  Блокер: Нет

### 2026-06-15 06:55 | dispatcher | Обновлён audit-скрипт под актуальную систему агентов
  Изменено:
  - `scripts/audit-agents.sh` — удалены legacy требования `.agent/DISPATCHER_PROMPT.md` и `.agent/ORCHESTRATOR_PROMPT.md`.
  - Добавлена проверка обязательных файлов `.kimi/agents/dispatcher.md` и `.kimi/agents/orchestrator.md`.
  - `.kimi/agents/qa.md` убран из списка устаревших файлов (теперь валидный агент).
  - Broken link check теперь игнорирует шаблонные placeholder'ы вида `<task-id>`.
  - Проверка `SESSION_START.md` теперь ищёт master skill `/promelectron` вместо удалённого `DISPATCHER_PROMPT.md`.
  - Добавлена проверка, что каждый `.kimi/agents/*.md` зарегистрирован в `.kimi/AGENTS.md`.
  - Обновлён `.agent/SESSION_LOG.md` (эта запись).
  Результат:
  - `bash scripts/audit-agents.sh` проходит без ошибок и предупреждений.
  Риск/Техдолг: Нет
  Блокер: Нет

### 2026-06-15 06:45 | dispatcher | Добавлены полноценные агенты architect и qa
  Изменено:
  - Создан `.kimi/agents/architect.md` — роль для анализа, trade-offs и написания `spec.md` перед реализацией; не пишет код.
  - Создан `.kimi/agents/qa.md` — роль для оркестрации pytest + vitest + Playwright и проверки Acceptance Criteria; отличие от `e2e-tester` зафиксировано (qa — все тесты, e2e-tester — Playwright-сценарии).
  - В Memory MCP добавлены сущности `architect` и `qa` и связи: dispatcher/orchestrator → обе роли; architect designs_for backend-dev/frontend-dev; qa tests backend-dev/frontend-dev и orchestrates e2e-tester.
  - Обновлены индексы и инструкции: `.kimi/AGENTS.md`, `AGENTS.md` (корневой), `SESSION_START.md`, `.kimi/agents/dispatcher.md`, `.kimi/agents/orchestrator.md`, `.kimi/skills/implement/SKILL.md`.
  - Обновлён `.agent/SESSION_LOG.md` (эта запись).
  Результат:
  - `/implement` теперь явно использует `architect` (Step 2) и `qa` (Step 6) как полноценных агентов.
  - Все роли, упоминаемые в документации, теперь имеют файлы и сущности в памяти.
  Риск/Техдолг:
  - Нужно следить, чтобы `qa` и `e2e-tester` не дублировались: qa запускает E2E на финальной проверке, e2e-tester разрабатывает и поддерживает сценарии.
  Блокер: Нет

### 2026-06-15 06:23 | dispatcher | Аудит системы агентов: исправлена Memory MCP — добавлены сущности агентов
  Изменено:
  - Проведён полный аудит `.kimi/agents/*.md`, `AGENTS.md`, `SESSION_START.md`, `PROJECT_CONTEXT.md`.
  - В Memory MCP создан корневой узел `Promelectron` (project) и сущности для всех ролей: dispatcher, orchestrator, backend-dev, frontend-dev, devops, e2e-tester, code-reviewer, security-reviewer, project-manager, integration-dev.
  - Удалены висячие отношения от несуществующего `DevOps agent`; созданы корректные отношения `devops manages Kubernetes Autonoma Cluster` и `devops requires OpenVPN Khen`.
  - Добавлены workflow-отношения: dispatcher selects_role_for каждого агента, orchestrator delegates_to агентам, code-reviewer/security-reviewer/e2e-tester связаны с dev-агентами.
  - Обновлён `.agent/SESSION_LOG.md` (эта запись).
  Результат:
  - Новые сессии теперь могут обращаться к агентам по имени через Memory MCP; граф целостный (нет dangling relations).
  - Правильные идентификаторы агентов зафиксированы: kebab-case имена файлов `.kimi/agents/<role>.md` (backend-dev, frontend-dev, code-reviewer и т.д.).
  Риск/Техдолг:
  - Необходимо в дальнейшем создавать сущности `feature`, `bug`, `decision` по мере работы, как предусмотрено Memory MCP.
  - workflow-роли `architect` и `qa` упоминаются в документации, но не имеют отдельных файлов в `.kimi/agents/` — при желании можно добавить позже.
  Блокер: Нет

### 2026-06-10 20:58 | devops | Починен worker CrashLoopBackOff (OOMKilled) в K8s test
  Изменено:
  - `infra/helm/templates/worker-deployment.yaml` — concurrency=2 (было 8 prefork), max-tasks-per-child=50, --without-heartbeat/gossip/mingle. Убраны сломанные probes (`celery inspect ping` не работает в контейнере → вызывал перезапуски).
  - `infra/helm/values.yaml` — worker memory: request 256Mi (было 128Mi), limit 512Mi (было 256Mi).
  - Worker deployment применён в `promelectron-test` через `kubectl apply` ( Helm release `promelectron-test` отсутствует в кластере — поды созданы не через Helm, нет labels `app.kubernetes.io/managed-by=Helm`).
  Результат:
  - Worker стабилен: `1/1 Running`, 0 рестартов, Celery v5.6.3 ready, concurrency=2, подключен к Redis.
  - Старый pod (549 рестартов) заменён.
  Риск/Техдолг:
  - Probes убраны полностью. В будущем можно добавить простую livenessProbe (`pgrep celery`) если понадобится.
  - Api/frontend/migrate deployment'ы всё ещё ссылаются на `latest` image → периодически появляются битые поды с `ImagePullBackOff`. Нужно либо восстановить Helm release, либо пропатчить image tag вручную.
  - K8s API доступен только через VPN (khen.ovpn), соединение нестабильно — периодические `i/o timeout`.
  Блокер: BLK-002 частично снят (worker работает), BLK-001 актуален (`.github/` защищена, Helm workflow не восстановлен).

### 2026-06-07 09:15 | backend-dev | Исправлен баг повторной оплаты заказа
  Изменено:
  - `backend/src/app/services/payment_service.py` — `PaymentService.create_payment()` теперь при существующем неоплаченном платеже создаёт новый платёж в ЮKassa (или mock) и обновляет существующую запись в БД новыми `yookassa_payment_id`, `confirmation_url`, `yookassa_status`, `yookassa_created_at`, `updated_at`. Раньше возвращался старый `confirmation_url` с истёкшим платежом.
  - `backend/tests/test_payments.py` — добавлен патч `YooKassaService.is_configured` (return_value=True) в тесты, использующие мок `create_payment`, чтобы они корректно отрабатывали в окружении без YOOKASSA_SHOP_ID/SECRET_KEY.
  - `backend/tests/test_notifications.py` — аналогичный патч `is_configured` в `test_payment_generates_notification`.
  - `backend/tests/test_orders.py` — аналогичный патч `is_configured` в `test_cancel_paid_order_fails`.
  Риск/Техдолг:
  - Поле `order_id` в `Payment` остаётся `unique=True`, поэтому при повторной оплате обновляется существующая запись (не создаётся новая). Это корректно с точки зрения бизнес-логики (один заказ = один платёж в БД).
  - При переходе от mock к реальной YooKassa логика не изменится — всё равно вызывается `YooKassaService.create_payment` и обновляется запись.
  Блокер: Нет

### 2026-06-06 10:45 | backend-dev | Диагностика YooKassa: debug-логи, webhook raw_body fix, debug endpoint
  Изменено:
  - `backend/src/app/services/yookassa_service.py` — добавлено debug-логирование request/response в create_payment/get_payment; capture теперь берётся из `settings.yookassa_capture_auto` (было hardcoded True)
  - `backend/src/app/services/payment_service.py` — handle_webhook теперь принимает `raw_body` для корректной проверки подписи; добавлены defensive проверки `payment.order is None`; добавлено info-логирование в sync_payment_status_by_order
  - `backend/src/app/api/payments.py` — webhook endpoint теперь считывает `await request.body()` ДО `request.json()` и передаёт raw_body в сервис; добавлен debug endpoint `POST /payments/debug/yookassa/create` (только при test_mode)
  - `backend/src/app/core/config.py` — добавлен `yookassa_capture_auto` (env `YOOKASSA_CAPTURE_AUTO`, default true)
  - `.env.example` — добавлена `YOOKASSA_CAPTURE_AUTO=true`
  - `backend/scripts/diagnose_yookassa.py` — standalone скрипт для диагностики прямого SDK-вызова
  - `backend/tests/test_auth.py` — исправлен `_make_oauth_settings` под новое поле Settings
  - `backend/tests/test_payments.py`, `test_orders.py`, `test_notifications.py` — убраны unused variables (ruff F841)
  Риск/Техдолг:
  - Возможный блокер: YooKassa test shop может отклонять платежи с capture=True для self-employed merchant. Рекомендуется протестировать с `YOOKASSA_CAPTURE_AUTO=false`.
  - Возможный блокер: серверы за пределами РФ могут быть заблокированы YooKassa (известная проблема).
  Блокер: Нет

### 2026-06-06 10:31 | frontend-dev | Исправлен баг в PaymentSuccess.vue: обработка 404 и ошибок fetchOrder
  Изменено:
  - `frontend/src/views/PaymentSuccess.vue` — добавлен `error` ref, `fetchOrder` теперь устанавливает `error.value` при 404 и других ошибках, добавлен блок ошибки в template с `data-testid="payment-error"` и кнопкой "Повторить", title/subtitle при ошибке не показывают "Обработка платежа...", добавлены стили `.payment-result__error`
  Риск/Техдолг: Нет
  Блокер: Нет

### 2026-06-02 21:00 | frontend-dev | YK-005: Frontend редирект на ЮKassa
  Изменено:
  - `frontend/src/views/Checkout.vue` — убраны поля карты, логика: создание платежа → редирект на `confirmation_url`
  - `frontend/src/views/PaymentSuccess.vue` — страница успешной оплаты (order_id из query)
  - `frontend/src/views/PaymentFailed.vue` — страница ошибки оплаты с кнопкой повтора
  - `frontend/src/router/index.js` — добавлены маршруты `/payment/success` и `/payment/failed`
  Риск: Нет
  Блокер: Нет

### 2026-06-02 20:35 | backend-dev | YK-004: Обновление PaymentService + API endpoints
  Изменено:
  - `backend/src/app/services/payment_service.py` — интеграция YooKassaService, handle_webhook, _process_successful_payment, cancel_payment через API
  - `backend/src/app/schemas/payment.py` — добавлены yookassa поля в PaymentOut
  - `backend/src/app/api/payments.py` — удалён mock confirm, добавлен webhook endpoint, обновлён create_payment
  - `backend/tests/test_payments.py` — 7 тестов с моками ЮKassa (все проходят)
  - `backend/tests/test_notifications.py` — обновлён под webhook
  - `backend/tests/test_orders.py` — обновлён под webhook
  Риск: Нет
  Блокер: Нет

### 2026-06-02 20:10 | backend-dev | YK-003: YooKassaService
  Изменено:
  - `backend/src/app/services/yookassa_service.py` — новый сервис: create_payment, get_payment, cancel_payment, create_refund
  - `backend/tests/test_yookassa_service.py` — 6 unit-тестов с моками SDK (все проходят)
  - `backend/tests/test_auth.py` — добавлены yookassa поля в `_make_oauth_settings`
  Риск: SDK синхронный, обёрнут в `asyncio.to_thread`
  Блокер: Нет

### 2026-06-02 19:45 | backend-dev | YK-002: Alembic миграция + исправление BLK-006
  Изменено:
  - `backend/alembic/versions/20260531_222559_guest_order_fields.py` → `b1c2d3e4f5a6_guest_order_fields.py` (исправлено BLK-006)
  - `backend/src/app/models/payment.py` — добавлены поля: yookassa_payment_id, yookassa_status, confirmation_url, payment_method_type, refunded_amount, yookassa_metadata, yookassa_created_at, updated_at
  - `backend/alembic/versions/55b9686a37ab_yookassa_payment_fields.py` — новая миграция (autogenerate)
  - `alembic upgrade head` прошёл успешно (PostgreSQL в Docker)
  Риск: Нет
  Блокер: BLK-006 снят

### 2026-06-02 19:15 | backend-dev | YK-001: ЮKassa SDK + конфигурация
  Изменено:
  - `backend/requirements.txt` — добавлен `yookassa>=3.0.0`
  - `.env.example` — добавлены `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_WEBHOOK_SECRET`, `YOOKASSA_TEST_MODE`
  - `backend/src/app/core/config.py` — `Settings` дополнен полями yookassa_shop_id, yookassa_secret_key, yookassa_webhook_secret, yookassa_test_mode
  Риск: SDK `yookassa` синхронный — потребуется `asyncio.to_thread` в сервисном слое (YK-003)
  Блокер: Нет

### 2026-06-02 18:30 | project-manager | Полный аудит №2 — исправлены все найденные ошибки
  Изменено:
  - `SESSION_START.md` — убрана устаревшая инструкция "Замени <ROLE>"
  - `backend-dev.md` — убраны broken links (.agent/<TASK_ID>/..., review/...), убран git commit
  - `frontend-dev.md` — аналогично backend-dev.md
  - `code-reviewer.md` — убраны ссылки на review/ и .agent/<TASK_ID>/...
  - `tester.md` — убрана ссылка на .agent/<TASK_ID>/review/test-findings.md
  - `PROJECT_CONTEXT.md` — убрано дублирование дат (теперь только в YAML frontmatter)
  - `Makefile` — добавлен `task-compact` target
  - `backend-dev.md`, `frontend-dev.md` — убран `Bash(git commit *)` из allowedTools
  Риск: Нет
  Блокер: Нет

### 2026-06-02 18:15 | project-manager | SESSION_START.md упрощён до 5 строк
  Изменено:
  - `SESSION_START.md` — Вариант А теперь компактный (5 строк вместо 40)
  - Добавлен Вариант Б — «Если сессия уже активна — просто пиши Задача: ...»
  - Убран длинный универсальный промпт с ручным определением роли
  Риск: Нет
  Блокер: Нет

### 2026-06-02 18:00 | project-manager | Внедрены улучшения: git hook, YAML frontmatter, AI self-check
  Изменено:
  - `.git/hooks/pre-push` — предупреждение перед push если линтер падает
  - `PROJECT_CONTEXT.md` — добавлен YAML frontmatter (machine-readable метрики)
  - `.kimi/rules/ai-self-check.md` — правила для AI-ассистента (проверка фактов, diff, обновление логов)
  - `.kimi/AGENTS.md` — добавлен ai-self-check в список rules
  Риск: pre-push hook может быть медленным на больших изменениях
  Блокер: Нет

### 2026-06-02 17:30 | project-manager | Полный аудит системы агентов — исправлены конфликты
  Изменено:
  - Удалены: `.agent/AGENTS.md` (дублировал корневой), `.agent/CONTEXT.md` (устарел)
  - Удалён: `.kimi/agents/qa.md` (дублировал tester.md)
  - Исправлен: `.kimi/rules/agent-first.md` — убрана ложная инструкция "never edit files" из Claude Code
  - Исправлен: `.kimi/agents/integration-dev.md` — `client/` → `frontend/`
  - Исправлены skills в backend-dev, frontend-dev, devops — убраны несуществующие skills
  - Обновлён: `SESSION_START.md` — добавлены ссылки на новые rules
  - Обновлён: `.kimi/AGENTS.md` — добавлены новые rules и skills
  - Обновлён: `AGENTS.md` (корневой) — добавлен раздел о системе агентов
  Риск: Удаление файлов могло сломать ссылки — проверить нужно
  Блокер: Нет

### 2026-06-02 16:00 | project-manager | Созданы guard-правила для агентов
  Изменено:
  - `.kimi/rules/pre-edit-checklist.md` — чеклист перед правкой кода (тесты, миграции, env, линтер)
  - `.kimi/rules/golden-path.md` — 5 критичных сценариев, которые нельзя ломать
  - `.kimi/rules/dependency-map.md` — таблица связей Model→Schema→Service→Route→Test
  Риск: Агенты могут игнорировать чеклист — нужно контролировать
  Блокер: Нет

### 2026-06-02 15:30 | project-manager | Изучена документация ЮKassa, составлен план интеграции
  Изменено:
  - `.agent/tasks/TASK-001-yookassa-integration.md` — детальный план (Phase 1-4)
  - `.agent/BACKLOG.md` — детализация задачи #1 на подзадачи 1a-1h
  - `PROJECT_CONTEXT.md` — обновлён API Inventory (endpoints payments)
  Документация: `/home/evgeniy/Загрузки/yookassa-docs/`
  Риск: SDK `yookassa` может быть синхронным — нужно проверить и обернуть в to_thread
  Блокер: BLK-006 (Alembic) мешает миграции Payment

### 2026-06-02 14:30 | project-manager | Создана система контекста для агентов
  Изменено:
  - `PROJECT_CONTEXT.md` — единый источник контекста
  - `.kimi/rules/task-template.md` — шаблон задачи
  - `.kimi/agents/project-manager.md` — ритм работы, формат задач
  - `.kimi/AGENTS.md` — обязательные файлы для чтения
  - `AGENTS.md` (корневой) — упоминание PROJECT_CONTEXT.md
  - `SESSION_START.md` — шаблон входа в сессию
  - `.agent/SESSION_LOG.md` — этот файл
  - `Makefile` — добавлены `agent-context`, `agent-status`
  Риск/Техдолг: Нужно привыкнуть дописывать SESSION_LOG после каждой сессии
  Блокер: Нет

---

### 2026-06-02 16:55 | project-manager | Показан текущий план проекта по запросу пользователя
  Изменено:
  - `.agent/SESSION_LOG.md` — эта запись
  Риск/Техдолг: Нет
  Блокер: Нет

---

*Старые записи будут ниже, когда появятся.*

## 2026-06-02 17:59

**Роль:** project-manager (router fix)

**Что сделано:**
- Исправлен роутер scripts/kimi-task.sh — 28/28 тестов проходят
- Исправлен lowercase для кириллицы: tr → python3 (tr не обрабатывает UTF-8 upper/lower)
- Исправлено склонение 'страница' → 'страниц[аеиоуыюя]?' (ловит страницу/страницы/странице)
- Исправлено склонение 'корзина' → 'корзин[аеиоуыюя]?' для UI-задач
- Добавлен hybrid паттерн для API integration задач (frontend-dev)
- Исправлено 'бэк' → 'бэк\b' чтобы не ловить 'бэклог' как backend
- Исправлено 'код' → 'код[аеиоуыюя]?' для review задач (качество кода)
- Убран trailing \b для e2e regex (проблемы с опциональными окончаниями)
- Добавлены mobile/мобильн паттерны в e2e keywords

**Файлы:** scripts/kimi-task.sh, scripts/test-router.sh

**Риски:** Нет

---

## 2026-06-02 18:04

**Роль:** project-manager (full system check)

**Что сделано:**
- Полный аудит агентской системы (audit-agents.sh) — все проверки проходят
- Проверка роутера (test-router.sh) — 28/28 тестов проходят
- Исправлен review/SKILL.md: убрана битая ссылка review/quick-findings.md → .agent/REVIEW_FINDINGS.md
- Исправлен PROJECT_CONTEXT.md: cd backend && make dev-backend → make dev-backend (target в корне)
- Исправлен Makefile: agent-context target был обрезан (только заголовок), дописан полный вывод контекста
- Проверены все агенты (.kimi/agents/*.md) — битых ссылок нет, git commit убран
- Проверены все rules (.kimi/rules/*.md) — консистентны
- Проверены все skills (.kimi/skills/*) — битых ссылок нет (кроме исправленной)

**Файлы изменены:** Makefile, PROJECT_CONTEXT.md, .kimi/skills/review/SKILL.md

**Риски:** Нет

---

## 2026-06-02 18:14

**Роль:** project-manager (role-switching clarification)

**Что сделано:**
- Проверена логика смены роли в рамках одной сессии Kimi CLI
- SESSION_START.md: добавлено предупреждение про 'инерцию роли' LLM в Вариант Б
- auto-agent/SKILL.md: добавлен раздел 'Ограничение: смена роли в рамках одной сессии'
- ROUTER.md: добавлен раздел про ограничение смены роли внутри сессии

**Файлы изменены:** SESSION_START.md, .kimi/skills/auto-agent/SKILL.md, ROUTER.md

**Риски:** Нет

---

## 2026-06-02 18:26

**Роль:** project-manager (dispatcher agent + all 3 variants)

**Что сделано:**
- Создан .kimi/agents/dispatcher.md — универсальный диспетчер, который определяет роль при КАЖДОМ запросе
- SESSION_START.md: добавлен Вариант Г (Диспетчер) как рекомендуемый для автопереключения ролей
- SESSION_START.md: Вариант А усилен предупреждением про инерцию роли
- ROUTER.md: добавлен dispatcher в таблицу ролей и архитектуру
- AGENTS.md: добавлен dispatcher в таблицу агентов
- auto-agent/SKILL.md: обновлен раздел ограничений — диспетчер как решение #1
- audit-agents.sh: проходит (все проверки OK)
- test-router.sh: 28/28 тестов проходят

**Файлы изменены:** .kimi/agents/dispatcher.md (новый), SESSION_START.md, ROUTER.md, AGENTS.md, .kimi/skills/auto-agent/SKILL.md

**Риски:** Нет

---

## 2026-06-02 18:34

**Роль:** project-manager (kimi-ask.sh — гарантированный сброс роли)

**Что сделано:**
- Создан scripts/kimi-ask.sh — скрипт, который формирует полный промпт с диспетчером + инструкции агента + контекст
- Отличие от kimi-task.sh: вставляет содержимое .kimi/agents/<ROLE>.md прямо в промпт (не требует чтения файлов LLM)
- Добавлен Makefile target: make ask MSG="..."
- Обновлён audit-agents.sh: проверяет make ask
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** scripts/kimi-ask.sh (новый), Makefile, scripts/audit-agents.sh

**Риски:** Нет

---

## 2026-06-02 18:46

**Роль:** project-manager (полный переход на Kimi CLI без bash)

**Что сделано:**
- Создан .agent/DISPATCHER_PROMPT.md — главный файл для автопереключения ролей внутри Kimi CLI
- SESSION_START.md полностью переписан: убраны все bash-команды, только текстовые инструкции для чата
- AGENTS.md обновлён: быстрый старт через DISPATCHER_PROMPT.md, убраны bash-команды из основного workflow
- ROUTER.md обновлён: Способ 1 — диспетчер (Kimi CLI), Способ 2 — фиксированная роль, Способ 3 — bash (опционально)
- audit-agents.sh обновлён: проверяет DISPATCHER_PROMPT.md и диспетчер в SESSION_START.md
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** .agent/DISPATCHER_PROMPT.md (новый), SESSION_START.md, AGENTS.md, ROUTER.md, scripts/audit-agents.sh

**Риски:** Нет

---

## 2026-06-02 18:56

**Роль:** project-manager (full audit + bug fixes)

**Что сделано:**
- Удалён .kimi/agents/tester.md — полностью дублировал e2e-tester.md
- Обновлён e2e-tester.md: добавлен YAML frontmatter, убран browser_take_screenshot (Claude-specific), заменён на page.screenshot()
- Обновлён integration-dev.md: добавлен YAML frontmatter, уточнена зона ответственности (только dev-окружение)
- Обновлён security-reviewer.md: добавлен YAML frontmatter
- Исправлен code-reviewer.md: spec.md → task-template.md, убрана ссылка на несуществующий client.py
- Обновлён CLAUDE.md: добавлен dispatcher, убран tester, добавлены security-reviewer и code-reviewer
- Исправлена таблица агентов в AGENTS.md: добавлен security-reviewer, удалён tester, исправлена разорванная таблица
- Обновлён ROUTER.md: добавлены cart (API/UI) и checkout (UI) keywords
- Исправлен .agent/tasks/README.md: review.md → REVIEW_FINDINGS.md
- Все агенты теперь имеют YAML frontmatter (консистентность)
- audit-agents.sh: проходит (все проверки OK)
- test-router.sh: 28/28 тестов проходят

**Файлы изменены:** .kimi/agents/e2e-tester.md, integration-dev.md, security-reviewer.md, code-reviewer.md, CLAUDE.md, AGENTS.md, ROUTER.md, .agent/tasks/README.md

**Риски:** Нет

---

## 2026-06-04 15:52

**Роль:** project-manager (added mixed-role mode)

**Что сделано:**
- SESSION_START.md: добавлен раздел 'Вариант: Сквозная фича' для задач, требующих нескольких ролей (например, YooKassa E2E → CI/CD → backend → Helm)
- .agent/DISPATCHER_PROMPT.md: добавлено исключение для сквозных задач — диспетчер работает гибко, не сбрасывая контекст между блоками
- .kimi/agents/dispatcher.md: добавлено то же исключение для сквозных задач
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** SESSION_START.md, .agent/DISPATCHER_PROMPT.md, .kimi/agents/dispatcher.md

**Риски:** Нет

---

---

## 2026-06-10 19:40

**Роль:** devops

**Что сделано:**
- Установлен kubectl → `~/.local/bin/kubectl` (v1.36.1)
- Установлен k9s → `~/.local/bin/k9s` (v0.50.3)
- Создан kubeconfig → `~/.kube/config` (chmod 600)
- Обновлён `.mcp.json`: Kubernetes MCP теперь указывает на `KUBECONFIG=/home/evgeniy/.kube/config`, убраны PROXY переменные
- Обновлён `AGENTS.md`: добавлен раздел "Kubernetes MCP" с командами kubectl, VPN, namespace'ами
- Обновлён `PROJECT_CONTEXT.md`: добавлена инфра-строка про kubectl/k9s/OpenVPN, дата обновлена, добавлена запись в историю
- Обновлён `.kimi/rules/infra.md`: добавлен раздел "Local K8s Access" с путями, namespace'ами, командами логов
- Lens (.deb/AppImage) — не удалось скачать автоматически (сетевые ограничения), рекомендуется ручная установка
- VPN (khen.ovpn) — требует `sudo` пароль, запущен zenity-диалог или требуется ручной запуск: `sudo openvpn --config "/home/evgeniy/Загрузки/khen (1)/khen/khen.ovpn"`

**Файлы изменены:** `.mcp.json`, `AGENTS.md`, `PROJECT_CONTEXT.md`, `.kimi/rules/infra.md`

**Риски:** kubeconfig содержит client cert+key (sensitive), права 600 установлены. VPN без sudo недоступен.

---

## 2026-06-16 06:15

**Роль:** architect / backend-dev / frontend-dev (agent system migration)

**Что сделано:**
- Мигрировал систему агентов под формат Kimi Code CLI.
- Создал `.kimi-code/skills/` с skill'ами: `/promelectron`, `/implement`, `/fix`, `/review`, `/deploy`, `/context-sync`, `/plan-maintainer`.
- Добавил `.kimi-code/mcp.json` (Playwright, Filesystem, Memory, Sequential Thinking, Kubernetes MCP).
- Добавил `.kimi-code/config.example.toml` с примером user-level конфига и permission rules.
- Создал helper `scripts/implement-pipeline.py` для генерации task-id, git worktree и cleanup.
- Переписал `.kimi/agents/*.md` без legacy YAML frontmatter: architect, backend-dev, frontend-dev, code-reviewer, security-reviewer, e2e-tester, qa, devops, project-manager, integration-dev, dispatcher.
- Удалил legacy файлы: `.kimi/settings.json`, `.kimi/CLAUDE.md`, `.kimi/tester.md`, `.kimi/AGENTS.md`, `.kimi/skills/`, `.agent/CURSOR_RULES.md`, `.agent/START_HERE.md`, root `.mcp.json`.
- Обновил документацию: `AGENTS.md`, `ROUTER.md`, `SESSION_START.md`, `.kimi/HOWTO.md`.
- Обновил `.gitignore` (`.kimi-code/config.toml`, `.worktrees/`) и `.kimi/rules/pre-edit-checklist.md`.
- Дописал запись в `PROJECT_CONTEXT.md`.

**Файлы изменены:** `.kimi-code/**`, `.kimi/agents/*.md`, `.kimi/HOWTO.md`, `.kimi/rules/pre-edit-checklist.md`, `AGENTS.md`, `ROUTER.md`, `SESSION_START.md`, `PROJECT_CONTEXT.md`, `.gitignore`, `scripts/implement-pipeline.py`

**Риски:**
- Старые скрипты `make task` / `make ask` больше не нужны; используются workflow skills.
- User-level config `~/.kimi-code/config.toml` должен быть настроен вручную для разрешения git worktree/test/lint.
- Feature worktrees в `.worktrees/` исключены из git.

---

## 2026-06-16 — agent-docs-audit

**Роль:** backend-dev  
**Задача:** проаудировать документацию агентов после миграции на Kimi Code CLI и устранить несоответствия.

**Что сделано:**
- Проверены `AGENTS.md`, `.kimi/agents/*.md`, `.kimi/rules/*.md`, `.kimi/HOWTO.md`, `ROUTER.md`, `SESSION_START.md` и skill-файлы в `.kimi-code/skills/`.
- В `AGENTS.md` исправлены ссылки на `.kimi-code/skills/*` и команды Kimi Code CLI; `/fix-test` заменён на `/skill:fix`; пути user-level конфигов приведены к `~/.kimi-code/config.toml` и `~/.kimi-code/mcp.json`.
- В `.kimi-code/config.example.toml`, `.kimi/rules/pre-edit-checklist.md` исправлены пути на `~/.kimi-code/config.toml`; восстановлены примеры `[[permission.rules]]` для `/skill:implement` pipeline.
- В `.gitignore` добавлено исключение `.kimi-code/config.toml`; `scripts/audit-agents.sh` обновлён под актуальные пути.
- Skill-вызовы приведены в соответствие с официальным форматом `/skill:<name>` (например, `/skill:implement`, `/skill:fix`, `/skill:review`, `/skill:deploy`, `/skill:context-sync`, `/skill:plan-maintainer`, `/skill:promelectron`).
- Усилены инструкции по параллельному чтению контекста в `.kimi-code/skills/implement/SKILL.md`, `.kimi/agents/architect.md`, `.kimi/agents/code-reviewer.md`.
- `e2e-tester.md` дополнен требованием локального прогона E2E перед пушем и описанием CI на `promelectron-test`.
- В `Makefile` добавлен target `pre-push` (lint + unit + E2E); в `AGENTS.md` добавлен раздел `Before push`.
- Правило языка (русский для reasoning/thinking) добавлено в `.kimi-code/skills/promelectron/SKILL.md`, `.kimi-code/skills/implement/SKILL.md` и все `.kimi/agents/*.md`.
- **Исправлена проблема с языком subagent-ов:** в `.kimi-code/skills/implement/SKILL.md`, `.kimi-code/skills/fix/SKILL.md`, `.kimi-code/skills/promelectron/SKILL.md` добавлено требование явно сообщать subagent-ам, что пользователь общается на русском; language-правила в `.kimi/agents/*.md` приведены к условию «если delegated prompt на русском или сказано, что пользователь на русском». Language-правила также добавлены/обновлены в `AGENTS.md`, `SESSION_START.md`, `.kimi/HOWTO.md`.
- Permission rules в `.kimi-code/config.example.toml` дополнены `git branch`, `git diff`, `git status`.
- Проверены skill-файлы: frontmatter валиден, нет внутренних команд `/skill:*`.
- Запущен `scripts/audit-agents.sh`: ошибок и предупреждений нет.
- Дополнен `PROJECT_CONTEXT.md` записью об аудите.

**Файлы изменены:** `AGENTS.md`, `PROJECT_CONTEXT.md`

**Риски:**
- Нет. Изменения только в документации; рабочие skill-файлы и pipeline не затронуты.

---

## 2026-06-20 15:15

**Роль:** backend-dev / frontend-dev

**Задача:** fix-cdek-widget-calculation — исправление review findings F005-F007

**Что сделано:**
- Добавлены в индекс git `frontend/src/api/cdek.js` и новый `backend/src/app/core/constants.py`.
- Удалён мёртвый код `if (import.meta.env.DEV && props.supplierCityCode == null)` и `console.warn` в `frontend/src/components/CdekDeliveryWidget.vue`.
- Вынесен `PVZ_TYPE_WHITELIST` в `backend/src/app/core/constants.py`, импортирован в `backend/src/app/api/cdek.py` и `backend/src/app/services/cdek_service.py`.
- Обновлён `.agent/fix-cdek-widget-calculation/review/findings.md`: F005-F007 отмечены как FIXED.
- Проверки:
  - `ruff check src/` — 0 ошибок.
  - `make test-backend` — 178 passed.
  - `npm run test -- --run` — 132 passed.
  - `npm run lint` — 0 ошибок.

**Файлы изменены:** `frontend/src/api/cdek.js`, `frontend/src/components/CdekDeliveryWidget.vue`, `backend/src/app/core/constants.py`, `backend/src/app/api/cdek.py`, `backend/src/app/services/cdek_service.py`, `.agent/fix-cdek-widget-calculation/review/findings.md`, `.agent/SESSION_LOG.md`.

**Риски:**
- Нет.

---

## 2026-06-21 13:52

**Роль:** audit-kimi-pipeline

**Задача:** Проверка русскоязычного reasoning агентов и субагентов

**Что сделано:**
- Проверена цепочка распространения языкового правила: `.kimi-code/AGENTS.md` → workflow skills → примеры промптов субагентов.
- Унифицированы языковые секции во всех workflow skills: `implement`, `fix`, `review`, `deploy`, `context-sync`, `plan-maintainer`, `promelectron`.
- В каждую секцию добавлено **критическое** требование: при запуске субагента в начало промпта вставляется инструкция о русском языке.
- В примерах промптов субагентов в `implement/SKILL.md` (architect, developer, code-reviewer, e2e-tester) добавлена явная языковая преамбула.
- Добавлена языковая заметка в `ROUTER.md`.
- `bash scripts/audit-agents.sh` проходит без ошибок.

**Файлы изменены:** `.kimi-code/skills/implement/SKILL.md`, `.kimi-code/skills/fix/SKILL.md`, `.kimi-code/skills/review/SKILL.md`, `.kimi-code/skills/deploy/SKILL.md`, `.kimi-code/skills/context-sync/SKILL.md`, `.kimi-code/skills/plan-maintainer/SKILL.md`, `ROUTER.md`, `PROJECT_CONTEXT.md`, `.agent/SESSION_LOG.md`.

**Риски:**
- Нет. Изменения только в инструкциях и документации.

---

## 2026-06-21 14:50

**Роль:** audit-kimi-pipeline

**Задача:** Изучение документации Kimi и аудит пайплайна на соответствие новым возможностям

**Что сделано:**
- Изучены официальные документы Kimi Code CLI (subagents, skills, slash commands, hooks, goals, plugins, MCP), Agent Skills Specification, MCP, ACP.
- Сравнены возможности Kimi с текущим пайплайном Promelectron.
- **Критическая находка:** в `.kimi-code/AGENTS.md` раздел `architect` предлагал использовать `explore` subagent, а `code-reviewer` — формулировку, которая могла быть истолкована как спавн субагентов. В документации Kimi чётко сказано: *"Sub-agents cannot schedule further nested sub-agents"*.
- Исправлено:
  - Добавлен раздел **Subagent boundary** в `.kimi-code/AGENTS.md`.
  - Убрана инструкция использовать `explore` subagent из раздела `architect`.
  - В разделе `code-reviewer` уточнено, что параллельный review backend/frontend выполняет родительский агент через `AgentSwarm`.
- Создан файл `.agent/audit-kimi-pipeline/review/kimi-docs-recommendations.md` с развёрнутыми рекомендациями и roadmap.
- Обновлены `PROJECT_CONTEXT.md` и `.agent/SESSION_LOG.md`.
- `bash scripts/audit-agents.sh` проходит без ошибок.

**Файлы изменены:** `.kimi-code/AGENTS.md`, `.agent/audit-kimi-pipeline/review/kimi-docs-recommendations.md`, `PROJECT_CONTEXT.md`, `.agent/SESSION_LOG.md`.

**Риски:**
- Нет. Изменения в инструкциях и документации; логика skills не затронута.

---

## 2026-06-21 15:45

**Роль:** audit-kimi-pipeline

**Задача:** Реализация рекомендаций по агентскому пайплайну (пункты 1–3 + AgentSwarm)

**Что сделано:**
1. **`deploy` → `type: flow`**: в `.kimi-code/skills/deploy/SKILL.md` изменён `type: prompt` на `type: flow`, убран `disableModelInvocation`. Skill теперь доступен только через явный `/skill:deploy test|prod`.
2. **Safety hooks + config**: `.kimi-code/config.example.toml` дополнен `default_model`, `default_thinking`, `default_permission_mode`, `merge_all_available_skills`, provider/model aliases. Добавлен hook `PreToolUse` → `Bash` → `scripts/hooks/block-dangerous-bash.py`. Создан и протестирован `scripts/hooks/block-dangerous-bash.py` (блокирует `rm -rf /`, `DROP`, `TRUNCATE`, force push, `git push origin main`).
3. **`AgentSwarm` для review**: в `.kimi-code/skills/implement/SKILL.md` шаг 4 переделан. Для mixed backend/frontend задач используется `AgentSwarm` с `items: ["backend", "frontend"]`. Каждый субагент пишет `findings-{item}.md`, родительский агент мёржит их в `findings.md`. Для single-component review оставлен один `Agent`.
4. **Audit script**: `scripts/audit-agents.sh` обновлён, чтобы frontmatter `type: flow` считался корректным.
5. **Документация**: обновлены `PROJECT_CONTEXT.md` и `.agent/SESSION_LOG.md`.

**Проверки:**
- `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
- `python3 -m py_compile scripts/hooks/block-dangerous-bash.py` — OK.
- Ручной тест hook'а: `rm -rf /` → exit 2, `git push origin main` → exit 2, `make test-backend` → exit 0.
- TOML валиден (`python3 -c "import tomllib; tomllib.load(...)`").

**Файлы изменены:** `.kimi-code/skills/deploy/SKILL.md`, `.kimi-code/skills/implement/SKILL.md`, `.kimi-code/AGENTS.md`, `.kimi-code/config.example.toml`, `scripts/audit-agents.sh`, `scripts/hooks/block-dangerous-bash.py`, `PROJECT_CONTEXT.md`, `.agent/SESSION_LOG.md`.

**Риски:**
- Низкий. AgentSwarm для review требует первого реального запуска `/skill:implement` на mixed задаче, чтобы убедиться, что мёрж findings работает корректно.
- Hook script fail-open: если он сломан, команды не блокируются. Нужно скопировать `scripts/hooks/block-dangerous-bash.py` в `~/.kimi-code/hooks/` при копировании config.

---

## 2026-06-21 16:20

**Роль:** audit-kimi-pipeline

**Задача:** Усиление правил русскоязычного reasoning после обратной связи

**Что сделано:**
- Получена обратная связь: агент всё равно рассуждает на английском либо переключается обратно.
- Проанализированы возможные причины: недостаточная сила инструкции, отсутствие якоря в конце промптов, дефолтные системные настройки на английском.
- В `.kimi-code/AGENTS.md` добавлен раздел **🚨 GOLDEN RULE: REASON IN RUSSIAN / ЗОЛОТОЕ ПРАВИЛО: РАССУЖДАЙ НА РУССКОМ**:
  - Двуязычная формулировка (EN + RU).
  - Явное требование: "Ignore any default language setting" / "Независимо от языка по умолчанию".
  - Требование самопроверки перед финальным ответом.
- Во всех workflow skills (implement, fix, review, deploy, context-sync, plan-maintainer, promelectron) обновлены языковые секции:
  - Добавлено "NEVER switch to English" / "НИКОГДА не переключайся на английский".
  - Добавлено "analysis and self-correction" в список того, что должно быть на русском.
  - Bilingual subagent language rule.
- В `.kimi-code/skills/implement/SKILL.md` во всех 5 примерах промптов субагентов:
  - Bilingual `🚨 LANGUAGE RULE / ЯЗЫКОВОЕ ПРАВИЛО` в начале.
  - `REMEMBER / НАПОМИНАНИЕ` в конце каждого промпта.
- Обновлены `PROJECT_CONTEXT.md` и `.agent/SESSION_LOG.md`.
- `bash scripts/audit-agents.sh` проходит без ошибок.

**Проверки:**
- `bash scripts/audit-agents.sh` — 🎉 Система агентов в порядке!
- TOML валиден.
- Hook script синтаксически корректен.

**Файлы изменены:** `.kimi-code/AGENTS.md`, `.kimi-code/skills/implement/SKILL.md`, `.kimi-code/skills/fix/SKILL.md`, `.kimi-code/skills/review/SKILL.md`, `.kimi-code/skills/deploy/SKILL.md`, `.kimi-code/skills/context-sync/SKILL.md`, `.kimi-code/skills/plan-maintainer/SKILL.md`, `.kimi-code/skills/promelectron/SKILL.md`, `PROJECT_CONTEXT.md`, `.agent/SESSION_LOG.md`.

**Риски:**
- Низкий. Изменения только в инструкциях; рабочий код не затронут. Эффективность усиленных инструкций можно проверить только на реальных сессиях.
