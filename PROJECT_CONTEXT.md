---
sprint: "Sprint 1"
sprint_dates: "2026-06-01 — 2026-06-14"
last_update: "2026-06-22"
last_commit: "4590325"
commit_message: "docs: update SESSION_LOG and PROJECT_CONTEXT to reference v2 branch"
blockers_count: 2
blockers_p0: 0
blockers_p1: 2
backend_tests: "213/213 (not runnable locally on SQLite)"
frontend_tests: "175/175"
e2e_tests: "not run locally (requires dev stack + permissions)"
---

# PROJECT_CONTEXT — Promelectron

> **Единый источник контекста для всех агентов.**  
> Читай этот файл в начале каждой сессии. После значимых изменений — дописывай кратко внизу.

> **Метаданные в YAML frontmatter выше.** Не дублируйте здесь.
>
> **Последний коммит:** `2f77465` — guest checkout with auto-account creation + BLK-008 fix

---

## Стек (коротко)

| Слой | Технологии |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 **async**, PostgreSQL 16, Redis 7, MinIO, Celery |
| Frontend | Vue 3 + Vite + Composition API + Axios, nginx:alpine (runtime) |
| Infra | Docker Compose (dev), K8s Helm (prod), GitHub Actions self-hosted runner → Harbor, kubectl, k9s, OpenVPN |
| Tests | pytest (backend), vitest (frontend), Playwright (E2E) |
| Auth | JWT Bearer + localStorage (планируется HttpOnly cookies + refresh tokens) |

---

## Что работает прямо сейчас ✅

- [x] **Каталог** — товары, категории, фильтры, поиск с подсказками
- [x] **Корзина (авторизованная + гостевая)** — backend API + localStorage + merge при login
- [x] **Checkout** — гостевой чекаут без авторизации, авто-создание ЛК после первой покупки, привязка заказа и сохранение адреса
- [x] **OAuth** — Yandex ID + Google ID (production credentials из env)
- [x] **Админ-панель** — CRUD товаров, категорий, заказов
- [x] **Уведомления** — WebSocket real-time
- [x] **Загрузка файлов** — MinIO + local fallback
- [x] **ЮKassa (test)** — создание платежей, webhook, auto-capture, отмена, возврат
- [x] **CDEK доставка** — расчёт тарифов, выбор ПВЗ/двери, автосоздание заказа после оплаты, вебхуки статусов, таблица `cdek_status_history`, durable sync-задания `cdek_sync_jobs`, программная отмена заказа в CDEK
- [x] **Password reset** — токены с TTL 24ч, инвалидация остальных токенов после использования
- [x] **Тесты зелёные** — Backend 213/213 ✅, Frontend 165/165 ✅, E2E 3/3 ✅

---

## Что в работе / не работает 🔄

| Фича | Статус | Блокер | Примечание |
|------|--------|--------|------------|
| **ЮKassa (production креды)** | 🔄 in_progress | — | Test-режим работает. Нужны live-креды для prod. |
| **Убрать hardcoded secrets** | ✅ done | — | Все креды вынесены в GitHub Secrets / SOPS. SECRET_KEY восстановлен. |
| **Sentry (мониторинг)** | ⏳ todo | — | Backend + frontend |
| **Backup БД** | ⏳ todo | — | pg_dump → S3/MinIO |
| **Helm worker templates** | ✅ done | — | Celery worker работает в K8s. |
| **Product.price → Numeric(10,2)** | ⏳ todo | — | Ждёт отдельной задачи |
| **Malformed Alembic revision** | ✅ done | — | Миграции чистые, история корректна |

---

## Активные блокеры ⚠️

| ID | Уровень | Описание | Кто решает | Дедлайн |
|----|---------|----------|------------|---------|
| **BLK-005** | P1 | Нет реальных SMTP кредов — email в fallback-режиме (welcome email для гостевого чекаута логируется, но не отправляется) | project-manager | 2026-06-15 |
| **BLK-009** | P1 | CDEK widget-service `calculate` возвращает 502 на test-окружении при передаче адреса без `code`. Блокирует UI-выбор доставки гостем. | backend-dev / devops | 2026-06-23 |
| **BLK-010** | P1 | YooKassa webhook `payment.succeeded` не приходит на `/api/v1/payments/yookassa/webhook/` в test-окружении — заказ не переходит в `paid` без ручной синхронизации. Нужно настроить webhook URL в личном кабинете YooKassa. | devops / project-manager | 2026-06-23 |

> **Правило:** Блокер >2 дней — эскалация пользователю.

---

## Архитектурные ограничения 🧱

1. **SQLAlchemy 2.0 async** — все DB операции async. Никаких sync-библиотек в основном потоке.
2. **Monolith** — все домены в одном FastAPI приложении. Микросервисы не раньше Фазы 3.
3. **PostgreSQL single master** — нет read replicas.
4. **Redis single-node** — кэш, rate limit, Celery брокер на одном инстансе.
5. **JWT 30 минут** — нет refresh tokens. Пользователи перелогиниваются.
6. **Trailing slash обязателен** — `api.get('/categories/')`, не `'/categories'`. Иначе 307 → axios теряет заголовки.
7. **SQLite ≠ PostgreSQL** — тесты только в Docker (`make test-backend`), никогда на SQLite.
8. **SELECT FOR UPDATE** — для консистентности stock при параллельных запросах.
9. **Alembic миграции** — при старте приложения (планируется перенос в Helm hook).
10. **MinIO + Local fallback** — для хранения файлов.

---

## Критические зависимости 🔗

```
Реальные платежи (ЮKassa)  →  Sub-orders / Комиссия / Возвраты
Helm worker templates        →  Celery Beat / Email async / Background tasks
Product.price → Numeric      →  Product variants / Seller payouts
```

**Ключевое правило:** Нельзя начинать Sub-orders, Комиссию, Возвраты до реализации реальных платежей.

---

## API Inventory 🌐

> Актуальные endpoints. Обновляй при добавлении новых.

### Публичные (без auth)
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| GET | `/api/v1/products/` | ✅ | Каталог товаров |
| GET | `/api/v1/categories/` | ✅ | Категории (пагинация, фильтр по parent_id, поиск по name) |
| GET | `/api/v1/products/search/` | ✅ | Поиск с подсказками |
| POST | `/api/v1/guest-cart/` | ✅ | Создать гостевую корзину |
| GET | `/api/v1/guest-cart/{id}/` | ✅ | Получить гостевую корзину |
| POST | `/api/v1/cart/merge/` | ✅ | Merge гостевой корзины при login |
| POST | `/api/v1/orders/create-guest/` | ✅ | Создать гостевой заказ |
| GET | `/api/v1/orders/guest/{order_id}/` | ✅ | Получить гостевой заказ по email |
| POST | `/api/v1/payments/guest/{order_id}/` | ✅ | Создать гостевой платёж ЮKassa |
| POST | `/api/v1/payments/guest/{order_id}/mock-confirm/` | ✅ | Подтвердить mock-оплату гостевого заказа |
| POST | `/api/v1/auth/password-reset-request/` | ✅ | Запросить сброс пароля |
| POST | `/api/v1/auth/password-reset/` | ✅ | Подтвердить сброс пароля |

### Auth / OAuth
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| POST | `/api/v1/auth/register/` | ✅ | Регистрация |
| POST | `/api/v1/auth/login/` | ✅ | Логин (JWT) |
| POST | `/api/v1/auth/yandex/` | ✅ | OAuth Yandex callback |
| POST | `/api/v1/auth/google/` | ✅ | OAuth Google callback |
| GET | `/api/v1/auth/providers/` | ✅ | Доступность OAuth-провайдеров |

### Авторизованные
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| GET | `/api/v1/cart/` | ✅ | Корзина авторизованного |
| POST | `/api/v1/orders/` | ✅ | Создать заказ |
| GET | `/api/v1/orders/` | ✅ | История заказов |
| POST | `/api/v1/payments/{order_id}/` | ✅ | Создать платёж ЮKassa |
| POST | `/api/v1/payments/yookassa/webhook/` | ✅ | Webhook от ЮKassa (payment.succeeded / payment.canceled) |
| POST | `/api/v1/payments/{payment_id}/cancel/` | ✅ | Отменить платёж (до оплаты) |
| GET | `/api/v1/payments/{payment_id}/` | ✅ | Информация о платеже |
| POST | `/api/v1/payments/{payment_id}/cancel/` | ✅ | Отменить платёж |
| GET | `/api/v1/users/me/addresses/` | ✅ | Список адресов пользователя |
| POST | `/api/v1/users/me/addresses/` | ✅ | Добавить адрес пользователя |

### Админка
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| GET | `/api/v1/admin/products/` | ✅ | Список товаров (admin) |
| POST | `/api/v1/admin/products/` | ✅ | Создать товар |
| GET | `/api/v1/admin/orders/` | ✅ | Список заказов (admin) |
| GET | `/api/v1/admin/feature-flags` | ✅ | Список feature flags (admin) |
| PATCH | `/api/v1/admin/feature-flags/{flag}` | ✅ | Переключить feature flag (admin) |

> **Trailing slash обязателен во всех путях.**

### CDEK доставка
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| POST | `/api/v1/cdek/calculate/` | ✅ | Расчёт тарифов CDEK |
| GET | `/api/v1/cdek/pvz/` | ✅ | Список ПВЗ / постаматов |
| GET | `/api/v1/cdek/suggest-cities/` | ✅ | Подсказка городов |
| POST | `/api/v1/cdek/webhooks/cdek/` | ✅ | Webhook статусов CDEK |
| POST | `/api/v1/cdek/orders/{order_id}/resync/` | ✅ | Повторная отправка заказа в CDEK |
| GET/POST | `/api/v1/cdek/widget-service/` | ✅ | Публичный прокси официального виджета CDEK (offices/calculate) |
| GET | `/api/v1/supplier/profile/` | ✅ | Профиль поставщика (CDEK настройки) |
| PATCH | `/api/v1/supplier/profile/` | ✅ | Обновление CDEK настроек поставщика |

> **Trailing slash обязателен во всех путях.**

---

## Frontend Map 🗺️

> Ключевые компоненты и страницы. Обновляй при добавлении новых.

### Pages (Views)
| Страница | Файл | Pinia Store | API |
|----------|------|-------------|-----|
| Home | `src/views/HomeView.vue` | — | `/products/`, `/categories/` |
| ProductDetail | `src/views/ProductDetailView.vue` | — | `/products/{id}/` |
| Cart | `src/views/CartView.vue` | `useCart` | `/cart/`, `/guest-cart/` |
| GuestCheckout | `src/views/GuestCheckoutView.vue` | `useCart` | `/guest-cart/`, `/cdek/`, `/orders/create-guest/` |
| Checkout | `src/views/CheckoutView.vue` | `useCart` | `/orders/`, `/payments/` |
| PaymentSuccess | `src/views/PaymentSuccessView.vue` | — | `/payments/guest/{order_id}/mock-confirm/`, `/orders/guest/{order_id}/` |
| PaymentFailed | `src/views/PaymentFailedView.vue` | — | `/payments/{payment_id}/` |
| Login | `src/views/LoginView.vue` | `useAuth` | `/auth/login/`, `/auth/yandex/` |
| ForgotPassword | `src/views/ForgotPassword.vue` | — | `/auth/password-reset-request/` |
| ResetPassword | `src/views/ResetPassword.vue` | — | `/auth/password-reset/` |
| AdminDashboard | `src/views/admin/DashboardView.vue` | — | `/admin/...` |
| Admin | `src/views/Admin.vue` | — | `/categories/` |

### Composables
| Composable | Файл | Отвечает за |
|------------|------|-------------|
| `useCart` | `src/composables/useCart.js` | Корзина (гость + auth, localStorage, merge) |
| `useGuestCheckout` | `src/composables/useGuestCheckout.js` | Валидация гостевого чекаута, нормализация телефона, сбор payload заказа |
| `useAuth` | `src/composables/useAuth.js` | JWT, OAuth, login/logout |
| `useSearch` | `src/composables/useSearch.js` | Поиск, подсказки, история |
| `useCategories` | `src/composables/useCategories.js` | Загрузка категорий, вкладки, поиск, пагинация |
| `usePayment` | `src/composables/usePayment.js` | Создание и статус платежей |

### Key Components
| Компонент | Файл | Где используется |
|-----------|------|------------------|
| `SearchBar` | `src/components/SearchBar.vue` | HomeView, AppHeader |
| `ProductGrid` | `src/components/ProductGrid.vue` | HomeView, CategoryView |
| `CartItemList` | `src/components/cart/CartItemList.vue` | CartView |
| `CheckoutButton` | `src/components/cart/CheckoutButton.vue` | CartView |
| `CdekDeliveryWidget` | `src/components/CdekDeliveryWidget.vue` | CartView, GuestCheckoutView |
| `GuestCheckoutForm` | `src/components/GuestCheckoutForm.vue` | GuestCheckoutView |
| `ProductFormModal` | `src/components/ProductFormModal.vue` | Admin товары (вес/габариты) |

---

## Как запускать проект

```bash
# Полный стек (Docker Compose)
make dev

# Backend только
make dev-backend

# Frontend только
cd frontend && npm run dev

# Tests
make test          # backend + frontend
make test-e2e      # Playwright
```

---

## История изменений (кратко)

| Дата | Что изменилось | Кто |
|------|---------------|-----|
| 2026-06-22 | **bugfix/guest-checkout-polish-v2**: исправлены два дефекта гостевого чекаута. (1) `YooKassaService._build_return_url` теперь включает `guest_email` в return URL — success page может загружать заказ без авторизации после редиректа от YooKassa (`backend/src/app/services/yookassa_service.py`, `payment_service.py`). (2) Добавлены страницы сброса пароля `ForgotPassword.vue` и `ResetPassword.vue`, роуты `/forgot-password` и `/reset-password`, ссылка «Забыли пароль?» на `/login`, unit-тесты (175/175 ✅). Ветка `bugfix/guest-checkout-polish-v2` запушена. BLK-011 закрыт. BLK-005 (SMTP) остаётся на следующую сессию. | backend-dev / frontend-dev |
| 2026-06-22 | **Agent pipeline health & worktree hygiene**: расширен `scripts/implement-pipeline.py` — добавлены `check-health`, `create-worktree --shared-node-modules`, `fix-permissions`, `archive-session-log`. Добавлены `Makefile` target'ы `worktree-health`, `fix-permissions`, `archive-session-log`. В `.kimi-code/skills/implement/SKILL.md` интегрированы health-check и shared `node_modules` в workflow. В `.kimi-code/rules/agent-commons.md` добавлены правила `Environment Health Check` и `Worktree Hygiene`. Архивировано 519 строк из `SESSION_LOG.md` (96.5 → 56.8 KB). Auto-cleanup worktree не добавлен — lifecycle остаётся под контролем пользователя. | backend-dev |
| 2026-06-22 | **CDEK status sync + cancel (backend)**: выделена доменная модель `CdekOrder` с `CdekStatusHistory` и `CdekSyncJob`; добавлена Alembic-миграция `1c463a2c2e3f` с миграцией старых CDEK-полей из `orders`; `CdekService.apply_cdek_status` нормализует вебхуки и обновляет `Order.status`; `CdekService.cancel_cdek_order` удаляет заказ в CDEK; Celery task `sync_cdek_jobs_task` выполняет периодическую синхронизацию статусов; добавлены unit-тесты (`test_cdek.py`, `test_auth.py`). Backend-тесты: 185/185 ✅, линтер чисто ✅. | backend-dev |
| 2026-06-21 | **Agent docs refactor**: `.kimi-code/AGENTS.md` сокращён до project-wide index; создан `.kimi-code/BUNDLE.md` — единый реестр role/workflow skills и shared rules; дублирующиеся секции вынесены в `.kimi-code/rules/agent-commons.md`, `planning.md`, `known-pitfalls.md`; `/skill:qa` интегрирован в `/skill:implement`; `project-manager` и `plan-maintainer` разделены; `disableModelInvocation: true` добавлен в ролевые skills; ссылки на rules унифицированы в формат `[Rule: Name](path)`; в `/skill:implement` добавлен перезапуск тестов перед повторным review; `scripts/audit-agents.sh` обновлён под новую структуру и улучшен regex для Markdown-ссылок. `bash scripts/audit-agents.sh` проходит без ошибок. | architect / backend-dev |
| 2026-06-21 | **Strengthened Russian reasoning rules**: усилены правила русскоязычного reasoning после обратной связи, что агент переключается на английский. В `.kimi-code/AGENTS.md` добавлен раздел **GOLDEN RULE: REASON IN RUSSIAN / ЗОЛОТОЕ ПРАВИЛО: РАССУЖДАЙ НА РУССКОМ** с двуязычной формулировкой, требованием самопроверки и инструкцией игнорировать дефолтные языковые настройки. Во всех workflow skills (implement, fix, review, deploy, context-sync, plan-maintainer, promelectron) обновлены языковые секции. В примерах промптов субагентов в `implement/SKILL.md` добавлены bilingual language rule в начало и REMEMBER / НАПОМИНАНИЕ в конец каждого промпта. `bash scripts/audit-agents.sh` проходит без ошибок. | audit-kimi-pipeline |
| 2026-06-21 | **Agent pipeline improvements implemented**: реализованы рекомендации из аудита Kimi docs. `deploy` skill переведён в `type: flow` (только ручной запуск). В `.kimi-code/config.example.toml` добавлены `default_model`, `default_thinking`, `default_permission_mode`, `merge_all_available_skills`, provider/model aliases, safety hook `PreToolUse` для блокировки опасных Bash-команд. Создан `scripts/hooks/block-dangerous-bash.py`. В `/skill:implement` добавлен `AgentSwarm` для параллельного backend/frontend review с мёржем findings. Обновлен раздел `code-reviewer` в `.kimi-code/AGENTS.md`. Audit script обновлён для поддержки `type: flow`. `bash scripts/audit-agents.sh` проходит без ошибок. | audit-kimi-pipeline |
| 2026-06-21 | **Kimi docs review & pipeline recommendations**: изучена документация Kimi Code CLI, Agent Skills, MCP, ACP. Проведено сравнение с текущим пайплайном Promelectron. Исправлено нарушение ограничения "subagents cannot schedule nested subagents" в `.kimi-code/AGENTS.md` (architect/code-reviewer). Добавлен раздел **Subagent boundary**. Создан файл рекомендаций `.agent/audit-kimi-pipeline/review/kimi-docs-recommendations.md` с roadmap: `type: flow` для deploy, safety hooks, `AgentSwarm` для параллельного review, типизированные аргументы skills, sub-skills, plugin, `/goal`. `bash scripts/audit-agents.sh` проходит без ошибок. | audit-kimi-pipeline |
| 2026-06-21 | **Russian-language reasoning consistency**: проверено, что агенты и субагенты ведут размышление на русском языке при русском запросе пользователя. Дополнены и унифицированы языковые секции во всех workflow skills (implement, fix, review, deploy, context-sync, plan-maintainer, promelectron). В примерах промптов субагентов в `implement/SKILL.md` добавлена явная языковая преамбула. Добавлена языковая заметка в `ROUTER.md`. `bash scripts/audit-agents.sh` проходит без ошибок. | audit-kimi-pipeline |
| 2026-06-21 | **Agent system migration v2**: `.kimi/agents/*.md` и `.kimi/rules/*.md` перенесены в `.kimi-code/AGENTS.md` (project-level instructions). Директория `.kimi/` удалена. `HOWTO.md` и `lessons-learned.md` сохранены в `.kimi-code/HOWTO.md` и `.kimi-code/LESSONS_LEARNED.md`. Обновлены `AGENTS.md`, `SESSION_START.md`, `ROUTER.md`, workflow skills, `scripts/audit-agents.sh`, `.claude/rules/agent-context.md`. Исправлен `.kimi-code/config.example.toml`: push в main → `ask`, удалено `default_yolo`, удалён project-specific hook. `bash scripts/audit-agents.sh` проходит без ошибок. | audit-kimi-pipeline |
| 2026-06-20 | **fix-cdek-widget-calculation (frontend)**: `CdekDeliveryWidget.vue` теперь принимает `supplierCityCode` и передаёт в виджет `from: { code: supplierCityCode }` вместо строки 'Москва'; `Cart.vue` и `GuestCheckout.vue` определяют `supplierId` из первого товара, загружают код города отправления через `GET /cdek/supplier-city-code/{supplier_id}/` и передают в виджет (fallback 44 при ошибке); создан `frontend/src/api/cdek.js`; в `useCart.js` гостевые товары сохраняют `supplier_id`; обновлены unit-тесты (`CdekDeliveryWidget.spec.js`, `Cart.spec.js`, `GuestCheckout.spec.js`); в `e2e/cdek-widget.spec.js` добавлен сценарий выбора ПВЗ с проверкой тарифа/цены. Frontend-тесты: 128/128 ✅, линтер чисто ✅. | frontend-dev |
| 2026-06-18 | **cdek-widget-recipient-name (frontend)**: `CdekDeliveryWidget.vue` переписан под официальный виджет `@cdek-it/widget@3` (загрузка с CDN, уничтожение при unmount, нормализация `onChoose` в `CdekDeliveryIn`, `servicePath: /api/v1/cdek/widget-service/`); в `Cart.vue` добавлены поля имени/фамилии получателя и валидация перед созданием заказа; `GuestCheckout.vue` заменил единое поле `guestName` на раздельные `guest_first_name`/`guest_last_name` и передаёт `recipient_first_name`/`recipient_last_name`; `Checkout.vue` отображает получателя; добавлен `VITE_YANDEX_MAPS_API_KEY` в `.env.example`; обновлены unit-тесты (`GuestCheckout.spec.js`, `Checkout.spec.js`, `Cart.spec.js`) и добавлен `CdekDeliveryWidget.spec.js`; E2E `checkout.spec.js` адаптирован под мок официального виджета. Frontend-тесты: 125/125 ✅, линтер чисто ✅. | frontend-dev |
| 2026-06-18 | **cdek-widget-recipient-name (backend)**: добавлены `recipient_first_name` / `recipient_last_name` в модель `Order`, схемы `OrderCreate`/`GuestOrderCreate`/`OrderOut` и `OrderService`; `CdekService._build_recipient` формирует имя из раздельных полей с fallback на `user.full_name`/`guest_name`; новый публичный endpoint `/api/v1/cdek/widget-service/` проксирует `action=offices` и `action=calculate` через `CdekClient`; добавлена Alembic-миграция `becdb9cce9b1`; обновлены backend-тесты (`test_cdek.py`, `test_orders.py`, `test_guest_orders.py`). Backend-тесты: 166/166 ✅. | backend-dev |
| 2026-06-16 | **admin-section-tabs (frontend)**: в `Admin.vue` добавлена единая горизонтальная таб-навигация по разделам админки (Дашборд, Пользователи, Категории, Способы доставки, Заказы, Фичатоглы) для десктопа и мобильных; по умолчанию активен Дашборд; добавлены `data-testid` для табов и панелей разделов. Обновлены unit-тесты `Admin.spec.js` и E2E `admin.spec.js`. Frontend-тесты: 108/108 ✅. | frontend-dev |
| 2026-06-16 | **admin-categories-tabs — final review + E2E**: исправлены замечания ревью (append в пагинации, debounce поиска, backend lint). Code review: APPROVED. E2E admin.spec.js: 2/2 ✅. Обновлены `PROJECT_CONTEXT.md` и `SESSION_LOG.md`. | code-reviewer / e2e-tester |
| 2026-06-16 | **Admin categories tabs (frontend)**: раздел «Категории» в `Admin.vue` переделан под горизонтальные вкладки корневых категорий + «Все» с фильтрацией дочерних; добавлен поиск, столбец «Товаров», пагинация «Показать ещё», empty-state; в модалке создания/редактирования добавлен селектор `parent_id`. Все потребители `GET /categories/` (`Admin.vue`, `ProductFormModal.vue`, `CategoryChips.vue`) адаптированы под `CategoryListOut`. Новые unit-тесты в `Admin.spec.js` и E2E-тест в `admin.spec.js`. | frontend-dev |
| 2026-06-16 | **Admin categories tabs (backend)**: `GET /categories/` теперь возвращает пагинированный список с `items`/`total`, поддерживает `skip`, `limit`, `parent_id`, `q`; `CategoryOut` дополнен `parent_id` и `product_count`; `CategoryService.list_categories` считает товары через `func.count`; добавлена защита от циклов в `update_category`. Новые тесты в `backend/tests/test_categories.py`. | backend-dev |
| 2026-06-16 | **Agent system migration**: migrated agent skills to Kimi Code CLI format in `.kimi-code/skills/` (`/implement`, `/fix`, `/review`, `/deploy`, `/context-sync`, `/plan-maintainer`, `/promelectron`). Added `.kimi-code/mcp.json` for MCP servers and `.kimi-code/config.example.toml` for user-level config. Rewrote `.kimi/agents/*.md` prompts without legacy YAML frontmatter. Created `scripts/implement-pipeline.py` helper for task IDs, git worktrees, and review-loop state. Updated `AGENTS.md`, `ROUTER.md`, `SESSION_START.md`, `.kimi/HOWTO.md`, `.gitignore`, and `.kimi/rules/pre-edit-checklist.md`. Removed legacy `.kimi/settings.json`, `.kimi/CLAUDE.md`, `.kimi/tester.md`, `.kimi/AGENTS.md`, `.kimi/skills/`, `.agent/CURSOR_RULES.md`, `.agent/START_HERE.md`, and root `.mcp.json`. | backend-dev / frontend-dev |
| 2026-06-15 | **Feature flags + Google OAuth toggle**: добавлен сервис `feature_flags.py` на Redis, endpoint `/auth/providers/`, guard на Google OAuth endpoints (`503` при отключении), frontend скрывает кнопку Google если провайдер недоступен. Админка: вкладка «Фичатоглы» + API `GET/PATCH /admin/feature-flags`. Новые тесты backend/frontend. Управление через `GOOGLE_OAUTH_ENABLED` env, Redis `feature:google_oauth` или UI админки. | backend-dev / frontend-dev |
| 2026-06-11 | **Исправлена YooKassa в test**: креды были `FILL_ME` → восстановлены тестовые. Исправлен CICD: `ImagePullBackOff` из-за `latest` → деплой по SHA. Восстановлен Secret `promelectron-secrets` (были удалены DATABASE_URL, SECRET_KEY). Полный флоу работает: регистрация → корзина → заказ → платёж. Коммит `9628457`. | devops |
| 2026-06-06 | YooKassa диагностика: добавлено debug-логирование, исправлен webhook raw_body bug, добавлен debug endpoint `/payments/debug/yookassa/create/`, capture теперь конфигурируется через `YOOKASSA_CAPTURE_AUTO`. 127 backend тестов зелёные. | backend-dev |
| 2026-06-03 | YooKassa E2E тест проходит с тестовой картой (5555...4444). Обновлён checkout.spec.js. 96/96 E2E + 127 backend тестов зелёные. | e2e-tester |
| 2026-06-03 | CI/CD готов к YooKassa: `.env.example`, Helm values (test/prod), GitHub Actions e2e.yml обновлены. Test/prod secrets уже содержат YOOKASSA_SHOP_ID/SECRET_KEY (SOPS). | devops |
| 2026-06-02 | Создан PROJECT_CONTEXT.md | project-manager |
| 2026-06-10 | Настроен локальный доступ к K8s: kubectl, k9s, kubeconfig, Kubernetes MCP, VPN (khen.ovpn). Кластер autonoma @ 30.30.30.20. Namespace: promenectron-test / promelectron. | devops |
