---
sprint: "Sprint 1"
sprint_dates: "2026-06-01 — 2026-06-14"
last_update: "2026-06-16"
last_commit: "f469859"
commit_message: "feat(admin): unified section tabs for admin panel"
blockers_count: 1
blockers_p0: 0
blockers_p1: 1
backend_tests: "166/166"
frontend_tests: "108/108"
e2e_tests: "98/98"
---

# PROJECT_CONTEXT — Promelectron

> **Единый источник контекста для всех агентов.**  
> Читай этот файл в начале каждой сессии. После значимых изменений — дописывай кратко внизу.

> **Метаданные в YAML frontmatter выше.** Не дублируйте здесь.
>
> **Последний коммит:** `f9c605d` — redirect guests to login on checkout

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
- [x] **Checkout** — redirect гостей на login перед оплатой
- [x] **OAuth** — Yandex ID + Google ID (production credentials из env)
- [x] **Админ-панель** — CRUD товаров, категорий, заказов
- [x] **Уведомления** — WebSocket real-time
- [x] **Загрузка файлов** — MinIO + local fallback
- [x] **ЮKassa (test)** — создание платежей, webhook, auto-capture, отмена, возврат
- [x] **CDEK доставка** — расчёт тарифов, выбор ПВЗ/двери, автосоздание заказа после оплаты, вебхуки статусов
- [x] **Тесты зелёные** — Backend 150/150 ✅, Frontend 101/101 ✅, E2E 96/96 ✅

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
| **BLK-005** | P1 | Нет реальных SMTP кредов — email в fallback-режиме | project-manager | 2026-06-15 |

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
| Checkout | `src/views/CheckoutView.vue` | `useCart` | `/orders/`, `/payments/` |
| Login | `src/views/LoginView.vue` | `useAuth` | `/auth/login/`, `/auth/yandex/` |
| AdminDashboard | `src/views/admin/DashboardView.vue` | — | `/admin/...` |
| Admin | `src/views/Admin.vue` | — | `/categories/` |

### Composables
| Composable | Файл | Отвечает за |
|------------|------|-------------|
| `useCart` | `src/composables/useCart.js` | Корзина (гость + auth, localStorage, merge) |
| `useAuth` | `src/composables/useAuth.js` | JWT, OAuth, login/logout |
| `useSearch` | `src/composables/useSearch.js` | Поиск, подсказки, история |
| `useCategories` | `src/composables/useCategories.js` | Загрузка категорий, вкладки, поиск, пагинация |

### Key Components
| Компонент | Файл | Где используется |
|-----------|------|------------------|
| `SearchBar` | `src/components/SearchBar.vue` | HomeView, AppHeader |
| `ProductGrid` | `src/components/ProductGrid.vue` | HomeView, CategoryView |
| `CartItemList` | `src/components/cart/CartItemList.vue` | CartView |
| `CheckoutButton` | `src/components/cart/CheckoutButton.vue` | CartView |
| `CdekDeliveryWidget` | `src/components/CdekDeliveryWidget.vue` | CartView, GuestCheckout |
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
