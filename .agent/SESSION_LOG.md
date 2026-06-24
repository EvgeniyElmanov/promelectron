### 2026-06-24 02:00 | architect | Пересмотр планов под отказ от Celery и универсальную таблицу jobs
  Изменено:
  - Получены новые требования от Александра: убрать Celery из проекта, использовать универсальную таблицу `jobs` в PostgreSQL и worker в бесконечном цикле; есть cronjobs для запуска задач по расписанию.
  - Проверено текущее состояние worktree `.worktrees/implement-cdek-status-sync-and-cancel`: реализован Celery-вариант (`cdek_tasks.py`, `celery_app.py`, `payment_service.py` вызывает `.delay()`).
  - Переписан `.agent/cdek-status-sync-and-cancel/spec.md`:
    - Отказ от Celery, переход на `jobs` + `job_worker.py`.
    - Job types: `CDEK_CREATE_ORDER`, `CDEK_SYNC_ORDER_STATUS`.
    - Cronjobs создают job'ы, worker их выполняет.
    - `payment_service.py` создаёт job вместо Celery task.
    - Обновлены Components Affected, Execution Plan, Must-haves, Risks.
    - Добавлен раздел "Варианты миграции Celery" (вариант 1 — только CDEK, вариант 2 — полный отказ).
  - Восстановлены `.agent/order-cancellation/task.md` и `spec.md` (были утеряны) с уточнением зависимости от helper'а `CdekService.cancel_cdek_order()`.
  Результат:
  - Планы адаптированы под требования Александра.
  - Требуется решение пользователя по варианту миграции Celery (CDEK-only vs полный отказ) и дальнейшие действия с worktree.
  Блокер: Нет.

### 2026-06-24 04:05 | devops / frontend-dev | fix frontend Node.js engine mismatch
  Роль: frontend-dev / devops.
  Запрос пользователя: «выполни рекомендуемое решение» для предупреждений EBADENGINE при `npm install`.
  Выполнено:
  - Диагностика: `vue-router@5.1.0` (разрешённый через `^5.0.4`) тянет `@babel/generator@^8.0.0-rc.4`, который требует Node.js `^22.18.0 || >=24.11.0`. Текущий Node v20.20.2 не удовлетворяет требованию.
  - Создан `frontend/.nvmrc` со значением `24`.
  - Обновлён `frontend/package.json` > `engines.node` с `^20.19.0 || >=22.12.0` на `^22.18.0 || >=24.11.0`.
  - Пересоздан `frontend/package-lock.json` под Node v24.15.0 / npm v11.12.1 (`rm -rf node_modules package-lock.json && npm install`).
  - Проверка: `npm install` — чисто, без EBADENGINE; `npm run build` — успешно.
  Результат:
  - Предупреждения `EBADENGINE` устранены. Frontend теперь официально требует Node.js 22.18+ или 24.x.
  - Файлы изменены: `frontend/.nvmrc`, `frontend/package.json`, `frontend/package-lock.json`.
  - Коммит не создан (требуется explicit user approval).

### 2026-06-22 21:40 | qa / backend-dev | guest-checkout-auto-account — manual test env verification & bugfix
  Роль: qa engineer + backend-dev.
  Запрос пользователя: «сделай полную проверку по всем пунктам» на test-окружении после merge в main.
  Выполнено:
  - Открыт https://promelectron-test.aidrivencode.ru в браузере (Playwright MCP): главная, каталог, корзина, гостевой чекаут загружаются.
  - CDEK виджет открывается, список ПВЗ загружается, но `action=calculate` возвращает 502 — UI-чекаут с доставкой заблокирован.
  - Создан гостевой заказ №330 через API, оплачен тестовой картой YooKassa 5555...4477 (с прохождением 3DS sandbox). Success page отображается при наличии `guest_email` в URL.
  - Webhook YooKassa не пришёл; статус заказа обновлён вручную через имитацию webhook. Пользователь автосоздан (user_id=1345), заказ привязан, welcome email не отправлен (SMTP_USER/SMTP_PASSWORD не заданы в test env).
  - Вход в ЛК по установленному вручную паролю работает; профиль и история заказов отображаются.
  - Повторный гостевой заказ №331 с тем же email привязался к тому же user_id=1345 (дубля нет).
  - Обычный авторизованный чекаут (заказ №332) работает и оплачивается.
  - Frontend unit tests: 165/165 ✅. Backend tests не запускались локально из-за SQLite. E2E не запускались локально (требуется dev stack).
  - Исправлен баг: `YooKassaService._build_return_url` теперь принимает `guest_email` и включает его в return URL; `PaymentService._create_or_update_payment` передаёт `guest_email` для гостевых платежей (и mock-режима). Это позволяет success page загружать заказ без авторизации после редиректа от YooKassa.
  - Обновлены артефакты: `PROJECT_CONTEXT.md`, `.agent/BLOCKERS.md` (BLK-007 resolved; добавлены BLK-009 CDEK 502, BLK-010 YooKassa webhook, BLK-011 frontend reset-password pages), `.agent/SESSION_LOG.md`.
  Результат:
  - Гостевой flow работает end-to-end на test env с обходом CDEK-502 через API.
  - Остались 3 активных блокера/дефекта: BLK-009 (CDEK calculate 502), BLK-010 (YooKassa webhook), BLK-011 (нет страниц сброса пароля).
  - Нужен explicit user approval для коммита bugfix'а return_url в main.

### 2026-06-22 22:35 | backend-dev / frontend-dev | guest-checkout-polish-v2 clean branch pushed
  Роль: backend-dev + frontend-dev.
  Запрос пользователя: одобрение на реализацию BLK-011 (страницы сброса пароля); BLK-005 отложить на следующую сессию; сделать чистую историю.
  Выполнено:
  - Из-за случайного `git add -A` в первом коммите старая ветка `bugfix/guest-checkout-polish` содержала revert + лишние артефакты.
  - Создана чистая ветка `bugfix/guest-checkout-polish-v2` от `main` с тремя аккуратными коммитами:
    - `af3afb9` — `fix(payments): include guest_email in YooKassa return_url for guest checkout success page`.
    - `c85e893` — `fix(auth): add forgot-password and reset-password pages for guest checkout users`.
    - `9b1efec` — `docs: update PROJECT_CONTEXT, BLOCKERS and SESSION_LOG for guest-checkout-polish`.
  - `npm run lint` — чисто ✅; `npm run test` — 175/175 ✅.
  - Локальный dev-server проверил: `/forgot-password` и `/reset-password?token=abc123` возвращают 200.
  - Обновлены артефакты: `PROJECT_CONTEXT.md`, `.agent/BLOCKERS.md` (BLK-011 закрыт), `.agent/SESSION_LOG.md`.
  Результат:
  - BLK-011 закрыт. Остались активные блокеры: BLK-005 (SMTP, отложен), BLK-009 (CDEK 502), BLK-010 (YooKassa webhook).
  - Ветка `bugfix/guest-checkout-polish-v2` готова к merge в main после review / explicit approval.

### 2026-06-22 20:25 | implement pipeline | guest-checkout-auto-account — implementation complete, ready for merge review
  Роль: orchestrator / implement pipeline.
  Выполнено:
  - Architect: техническая спецификация в `.agent/guest-checkout-auto-account/spec.md`.
  - Backend-dev: модели `UserAddress`, `PasswordResetToken`, миграция, guest endpoints, авто-создание/привязка пользователя после оплаты, сброс пароля, сохранение адреса.
  - Frontend-dev: гостевой чекаут (`GuestCheckout.vue`), `Cart.vue`, `Checkout.vue`, `PaymentSuccess.vue`, `PaymentFailed.vue`, E2E-сценарий.
  - Code review: 4 итерации (backend + frontend), статус APPROVED.
  - QA: backend 213/213 ✅, frontend unit 165/165 ✅, E2E checkout.spec.js 3/3 ✅ (с workaround `FRONTEND_URL=http://frontend:5173`).
  - Итоговая оценка токенов: `ESTIMATED_TOKENS=20465` (порог 180000).
  Результат:
  - Worktree: `.worktrees/implement-guest-checkout-auto-account/`
  - Feature branch: `feature/guest-checkout-auto-account`
  - Review status: APPROVED
  - Блокер: BLK-008 — `FRONTEND_URL=http://localhost:5173` в `backend/docker-compose.yml` ломает E2E внутри Docker (environment issue).

### 2026-06-22 20:05 | qa | guest-checkout-auto-account — QA cycle complete
  Роль: QA engineer.
  Выполнено:
  - Прочитаны task.md, spec.md, findings.md, PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, qa/SKILL.md, golden-path.md.
  - `make test-backend` — 213/213 ✅
  - `make test-frontend` — 165/165 ✅
  - `npx playwright test e2e/checkout.spec.js --workers=1`:
    - default dev-окружение: 2/3 ✅, 1 ❌ (гостевой mock-редирект падает с `chrome-error://chromewebdata/` / `net::ERR_CONNECTION_REFUSED` на `http://localhost:5173`).
    - с workaround `FRONTEND_URL=http://frontend:5173` для api: 3/3 ✅.
  - Acceptance Criteria из spec.md проверены: все выполнены на уровне кода; E2E AC1 требует корректного `FRONTEND_URL` в dev-конфиге.
  Результат:
  - Создан `.agent/guest-checkout-auto-account/review/test-findings.md`.
  - Добавлен блокер BLK-008 в `.agent/BLOCKERS.md`.
  - Обновлены `PROJECT_CONTEXT.md` (счётчики тестов, история).
  Блокер: BLK-008 — `FRONTEND_URL=http://localhost:5173` в `backend/docker-compose.yml` ломает E2E гостевого чекаута внутри Docker (environment issue, не код).

### 2026-06-22 19:42 | code-reviewer (backend) | guest-checkout-auto-account — final backend review APPROVED
  Проведено финальное ревью backend после исправлений iteration 3.
  Проверено:
  - Все backend findings из `.agent/guest-checkout-auto-account/review/findings.md` (F001–F013, F026–F028) подтверждены как исправленные.
  - `make test-backend` — 213/213 ✅ (после пересоздания чистой БД/тома из-за deadlock'ов в `conftest.py`).
  - `make test-frontend` — 165/165 ✅.
  - `ruff check src/ tests/` — чисто ✅.
  - Новых критических/высоких backend-проблем не выявлено.
  Результат:
  - `.agent/guest-checkout-auto-account/review/findings-backend-final.md` создан со статусом **APPROVED**.
  Блокер: Нет.

### 2026-06-22 18:55 | frontend-dev | guest-checkout-auto-account — frontend findings F015, F029-F033 fixes
  Изменено:
  - `frontend/src/composables/useGuestCheckout.js` — `normalizePhone` теперь обрабатывает 11-значные российские номера, начинающиеся с `8`, преобразуя их в `+7...` (F015). Убран лишний вызов `createGuestPayment` из `submitGuestCheckout`; платёж теперь создаётся только на `Checkout.vue` (F030).
  - `frontend/src/views/GuestCheckout.vue` — в `catch` блоке `loadSupplierCityCode` добавлен `console.error(...)` под `import.meta.env.DEV` (F033).
  - `frontend/src/views/PaymentFailed.vue` — добавлена поддержка гостевого режима: чтение `guest_email` из query-параметра, загрузка заказа через `getGuestOrder`, `retryPayment` с `guest_email`, скрытие ссылки «Мои заказы» для гостей, замена локального `formatPrice` на shared `formatPrice` из `@/utils/price` (F029, F031, F032).
  - `frontend/src/__tests__/GuestCheckout.spec.js` — обновлены тесты под отсутствие `createGuestPayment`, добавлен тест нормализации телефона с ведущей `8`, исправлен тест невалидного телефона.
  - `frontend/src/__tests__/useGuestCheckout.spec.js` — новый unit-тест для `normalizePhone` и `validateGuestForm`.
  - `frontend/src/__tests__/PaymentFailed.spec.js` — новый unit-тест для авторизованного и гостевого режимов.
  - `frontend/docker-compose.yml` — обновлён образ Playwright с `v1.60.0-jammy` до `v1.61.0-jammy`, чтобы соответствовать установленному пакету `playwright@1.61.0`.
  Результат:
  - `make test-frontend` — 165/165 ✅
  - `make lint-frontend` — чисто ✅
  - `npx playwright test e2e/checkout.spec.js --workers=1` — 2/3 ✅, 1 ❌. Гостевой сценарий падает на шаге редиректа после оплаты: `confirmation_url` от backend содержит `FRONTEND_URL=http://localhost:5173`, который внутри контейнера Playwright не доступен (получаем `chrome-error://chromewebdata/`). Остальные два checkout-теста проходят.
  Блокер: E2E-гостевой сценарий требует корректного `FRONTEND_URL` (например, `http://frontend:5173`) в backend docker-compose для запуска внутри контейнера.

### 2026-06-22 18:10 | frontend-dev | guest-checkout-auto-account — frontend findings F023-F025 fixes
  Изменено:
  - `frontend/src/views/GuestCheckout.vue` — после submit гостевого заказа всегда редиректит на `/checkout/:id?guest_email=...` (убран мгновенный редирект на `payment.confirmation_url`), чтобы соответствовать Acceptance Criteria и E2E-сценарию.
  - `frontend/src/views/PaymentSuccess.vue` — в `catch` блоке `confirmMockPayment` добавлен `console.error(...)` под `import.meta.env.DEV` (F024).
  - `frontend/src/api/users.js` — удалён неиспользуемый файл (F025).
  - `frontend/e2e/checkout.spec.js` — guest-сценарий обновлён: создание заказа, редирект на checkout, mock-оплата, проверка `/payment/success?mock=1` и статуса "Оплачен" (F023).
  - `frontend/src/__tests__/GuestCheckout.spec.js` — обновлён тест редиректа на `/checkout/42`; добавлен route `/checkout/:id` в тестовый router.
  - `frontend/src/views/Cart.vue` — добавлен trailing slash в `POST /orders/create/` для авторизованного создания заказа (исправление регресса F022 в UI).
  - `frontend/src/__tests__/Cart.spec.js` — обновлёно ожидание URL с trailing slash.
  Результат:
  - `npm run test -- --run` (в контейнере frontend) — 149/149 ✅
  - `npm run lint` (в контейнере frontend) — чисто ✅
  - `npx playwright test e2e/checkout.spec.js --workers=1` — 3/3 ✅
  Блокер: Нет.

### 2026-06-22 08:05 | backend-dev | guest-checkout-auto-account — trailing slash fixes (F013, F022)
  Изменено:
  - `backend/src/app/api/orders.py` — добавлен trailing slash ко всем route'ам (`/create/`, `/create-guest/`, `/guest/{order_id}/`, `/{order_id}/`, `/{order_id}/cancel/`, `/{order_id}/status/`, `/supplier/`, `/supplier/{order_id}/`, `/supplier/{order_id}/ship/`); supplier-роуты перенесены перед динамическим `/{order_id}/`, чтобы избежать перехвата `/supplier/`.
  - `backend/src/app/api/payments.py` — добавлен trailing slash ко всем route'ам (`/{order_id}/`, `/guest/{order_id}/`, `/guest/{order_id}/mock-confirm/`, `/{order_id}/mock-confirm/`, `/{payment_id}/`, `/{payment_id}/cancel/`, `/{payment_id}/sync/`, `/sync-by-order/{order_id}/`, `/debug/yookassa/create/`, `/yookassa/webhook/`).
  - `backend/tests/test_orders.py`, `test_guest_orders.py`, `test_payments.py`, `test_guest_payments.py`, `test_analytics.py`, `test_notifications.py` — все вызовы `/api/v1/orders/*` и `/api/v1/payments/*` приведены к trailing slash.
  Результат:
  - `make test-backend` — 207/207 ✅
  - `ruff check backend/src backend/tests` — чисто ✅
  - Исправлены findings F013 и F022 из `.agent/guest-checkout-auto-account/review/findings.md`.
  Блокер: Нет.

### 2026-06-22 15:52 | backend-dev | Улучшения агентского пайплайна: health-check, shared node_modules, fix-permissions, archive-session-log
  Изменено:
  - `scripts/implement-pipeline.py` — добавлены команды `check-health`, `create-worktree --shared-node-modules`, `fix-permissions`, `archive-session-log`.
  - `.kimi-code/skills/implement/SKILL.md` — интегрированы health-check, shared node_modules и fix-permissions в workflow.
  - `.kimi-code/rules/agent-commons.md` — добавлены разделы `Environment Health Check` и `Worktree Hygiene`.
  - `Makefile` — добавлены target'ы `worktree-health`, `fix-permissions`, `archive-session-log`.
  - `.agent/SESSION_LOG.md` — архивировано 519 строк (96.5 → 56.8 KB).
  - `PROJECT_CONTEXT.md` — добавлена запись в историю изменений.
  Результат:
  - `python -m py_compile scripts/implement-pipeline.py` ✅
  - `python -m ruff check scripts/implement-pipeline.py` ✅
  - `make worktree-health` работает и обнаруживает реальные предупреждения.
  - Тестовый worktree с shared node_modules занял 3.3M вместо ~300M.
  Блокер: Нет.

### 2026-06-22 09:05 | backend-dev | Реализована задача cdek-status-sync-and-cancel
  Изменено:
  - `backend/src/app/models/cdek_order.py` — новые модели `CdekOrder`, `CdekStatusHistory`, `CdekSyncJob`.
  - `backend/src/app/models/__init__.py` — экспорт новых моделей.
  - `backend/src/app/models/order.py` — замена CDEK-полей на `cdek_order_id` и relationship.
  - `backend/src/app/schemas/order.py` — обновление схем под `cdek_order`.
  - `backend/src/app/schemas/cdek_order.py` — новые схемы CDEK-моделей.
  - `backend/src/app/services/cdek_client.py` — добавлен `delete_order`, `get_order`.
  - `backend/src/app/services/cdek_service.py` — `apply_cdek_status`, `cancel_cdek_order`, нормализация webhook, маппинг статусов.
  - `backend/src/app/services/order_service.py` — использование `CdekOrder` при создании/отмене заказа.
  - `backend/src/app/services/payment_service.py` — создание `CdekOrder`/`CdekSyncJob` после оплаты.
  - `backend/src/app/workers/cdek_tasks.py` — Celery task `sync_cdek_jobs_task` + `create_cdek_order_task`.
  - `backend/src/app/workers/celery_app.py` — регистрация beat-расписания.
  - `backend/src/app/core/config.py` — новые настройки `cdek_sync_beat_interval_seconds`, `cdek_terminal_statuses`.
  - `backend/src/app/api/cdek.py` — обновление webhook + resync endpoint.
  - `backend/alembic/versions/1c463a2c2e3f_cdek_orders_tables_and_data_migration.py` — миграция с переносом данных.
  - `backend/tests/test_cdek.py` — 42 теста, покрывающие создание, webhook, polling sync, apply, idempotентность, отмену.
  - `backend/tests/test_auth.py` — добавлены новые CDEK-настройки в `_make_oauth_settings`.
  - `PROJECT_CONTEXT.md`, `.agent/BACKLOG.md` — обновлено состояние.
  Результат:
  - Backend-тесты: 185/185 ✅
  - Ruff check / format: чисто ✅
  - Миграция создана и корректна.
  Блокер: Нет.

### 2026-06-22 05:35 | architect | Скорректированы планы cdek-status-sync-and-cancel и order-cancellation
  Изменено:
  - `.agent/cdek-status-sync-and-cancel/spec.md`:
    - D-21: отказ от Celery заменён на использование Celery Beat + task `sync_cdek_jobs_task` для polling `cdek_sync_jobs`.
    - D-08, D-09, D-19: локальная отмена заказа вынесена в задачу `order-cancellation`; `cdek-status-sync-and-cancel` предоставляет helper `CdekService.cancel_cdek_order()`.
    - Worker Architecture: переписан под Celery Beat + task, убран `cdek_worker.py` в бесконечном цикле.
    - Components Affected: добавлены `cdek_tasks.py`, `celery_app.py`; убраны endpoint'ы отмены.
    - API Changes: убраны PATCH отмены; trailing slash проверен.
    - Execution Plan: убран Этап 4 "Отмена заказа", добавлен Этап с Celery task.
    - Must-haves / Acceptance Criteria: убраны пункты про отмену.
    - Out of Scope: добавлены endpoint'ы локальной отмены и refund через ЮKassa.
    - Risks: обновлён риск про взаимодействие с `order-cancellation`.
  - `.agent/order-cancellation/spec.md`:
    - Уточнён scope: задача отвечает за локальную отмену, CDEK-вызов делает через helper `CdekService.cancel_cdek_order()`.
    - Добавлен D-09 про использование helper'а из `cdek-status-sync-and-cancel`.
    - Technical Design: добавлен вызов helper'а для paid-заказов с `cdek_uuid`.
    - Components Affected: добавлен `cdek_service.py`.
    - Out of Scope: уточнено, что прямой CDEK API вызов живёт в `cdek-status-sync-and-cancel`.
    - Risks: добавлен риск зависимости от `cdek-status-sync-and-cancel`.
  Результат:
  - Планы одобрены пользователем с правками.
  - Celery оставлен для polling.
  - Scope между задачами разграничен: `cdek-status-sync-and-cancel` — синхронизация + CDEK helper; `order-cancellation` — локальная отмена + вызов helper'а.
  - Готовность к запуску `/implement`.
  Блокер: Нет.

### 2026-06-22 05:16 | architect | Анализ планов cdek-status-sync-and-cancel и order-cancellation по сообщениям Александра
  Изменено:
  - Изучены `.agent/cdek-status-sync-and-cancel/task.md` и `spec.md`.
  - Изучены `.agent/order-cancellation/task.md` и `spec.md`.
  - Проверены текущие модели и сервисы: `backend/src/app/models/order.py`, `services/cdek_service.py`, `services/cdek_client.py`, `services/order_service.py`, `api/orders.py`, `api/admin.py`, `schemas/order.py`.
  - Проверены frontend-views: `frontend/src/views/OrderDetail.vue`, `Orders.vue`, `Admin.vue`.
  Результат:
  - План в целом верный и покрывает требования Александра (статусы СДЭК, история, ссылка на отслеживание, webhook + polling, отмена до передачи в доставку, UI пользователя и админа).
  - Выявлены 3 критических замечания, требующих решения перед реализацией:
    1. **Отказ от Celery** в `cdek-status-sync-and-cancel/spec.md` противоречит текущей инфраструктуре проекта (уже есть Celery + Redis, cdek_tasks.py, celery_app.py). Рекомендуется оставить Celery Beat для polling.
    2. **Дублирование отмены** между `cdek-status-sync-and-cancel` и `order-cancellation`. Обе спецификации описывают отмену заказа, но с разными деталями. Нужно чётко разграничить scope или объединить задачи.
    3. **Worker в бесконечном цикле** без supervisor/liveness probe — риск для production. Если оставлять отдельный процесс, нужна инфраструктура мониторинга.
  - Даны рекомендации по корректировке плана (см. ответ пользователю).
  Блокер: Нет.

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

