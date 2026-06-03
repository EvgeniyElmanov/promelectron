---
sprint: "Sprint 1"
sprint_dates: "2026-06-01 — 2026-06-14"
last_update: "2026-06-03"
last_commit: "f9c605d"
commit_message: "feat(cart): redirect guests to login on checkout instead of guest-checkout"
blockers_count: 5
blockers_p0: 1
blockers_p1: 4
backend_tests: "123/123"
frontend_tests: "80/80"
e2e_tests: "96/96"
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
| Infra | Docker Compose (dev), K8s Helm (prod), GitHub Actions self-hosted runner → Harbor |
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
- [x] **Тесты зелёные** — Backend 127/127 ✅, Frontend 80/80 ✅, E2E 96/96 ✅

---

## Что в работе / не работает 🔄

| Фича | Статус | Блокер | Примечание |
|------|--------|--------|------------|
| **ЮKassa (реальные платежи)** | 🔄 in_progress | — | Заменяет mock-оплату. Webhook в todo. |
| **Убрать hardcoded secrets** | 🔄 in_progress | — | SECRET_KEY, SEED_SECRET, docker-compose, Helm placeholders |
| **Sentry (мониторинг)** | 🔄 in_progress | — | Backend + frontend |
| **Backup БД** | 🔄 in_progress | — | pg_dump → S3/MinIO |
| **Helm worker templates** | 🚫 blocked | BLK-001, BLK-002 | Celery command сломан, `worker.enabled=false` |
| **Product.price → Numeric(10,2)** | ⏳ todo | BLK-006 | Ждёт фикса миграции |
| **Malformed Alembic revision** | 🟡 in_progress | — | `20260531_222559_guest_order_fields.py` |

---

## Активные блокеры ⚠️

| ID | Уровень | Описание | Кто решает | Дедлайн |
|----|---------|----------|------------|---------|
| **BLK-002** | P0 | Celery worker в K8s полностью неработоспособен (сломанная команда + `enabled=false`) | devops | 2026-06-02 🔴 эскалирован |
| **BLK-001** | P1 | `.github/` защищена — CI/CD правки требуют ручного доступа | devops | 2026-06-02 🔴 эскалирован |
| **BLK-006** | P1 | Malformed revision ID в Alembic миграции `20260531_222559_guest_order_fields.py` | backend-dev | 2026-06-04 |
| **BLK-004** | P1 | `API_BASE_URL` в K8s test окружении не настроен | devops | 2026-06-05 |
| **BLK-005** | P1 | Нет реальных SMTP кредов — email в fallback-режиме | project-manager | 2026-06-10 |

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
| GET | `/api/v1/categories/` | ✅ | Категории |
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

### Авторизованные
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| GET | `/api/v1/cart/` | ✅ | Корзина авторизованного |
| POST | `/api/v1/orders/` | ✅ | Создать заказ |
| GET | `/api/v1/orders/` | ✅ | История заказов |
| POST | `/api/v1/payments/{order_id}/` | 🔄 | Создать платёж ЮKassa (was mock) |
| POST | `/api/v1/payments/yookassa/webhook/` | ⏳ | Webhook от ЮKassa |
| POST | `/api/v1/payments/{payment_id}/confirm/` | ❌ | **Удалить** — mock endpoint |
| GET | `/api/v1/payments/{payment_id}/` | ✅ | Информация о платеже |
| POST | `/api/v1/payments/{payment_id}/cancel/` | ✅ | Отменить платёж |

### Админка
| Метод | Путь | Статус | Описание |
|-------|------|--------|----------|
| GET | `/api/v1/admin/products/` | ✅ | Список товаров (admin) |
| POST | `/api/v1/admin/products/` | ✅ | Создать товар |
| GET | `/api/v1/admin/orders/` | ✅ | Список заказов (admin) |

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

### Composables
| Composable | Файл | Отвечает за |
|------------|------|-------------|
| `useCart` | `src/composables/useCart.js` | Корзина (гость + auth, localStorage, merge) |
| `useAuth` | `src/composables/useAuth.js` | JWT, OAuth, login/logout |
| `useSearch` | `src/composables/useSearch.js` | Поиск, подсказки, история |

### Key Components
| Компонент | Файл | Где используется |
|-----------|------|------------------|
| `SearchBar` | `src/components/SearchBar.vue` | HomeView, AppHeader |
| `ProductGrid` | `src/components/ProductGrid.vue` | HomeView, CategoryView |
| `CartItemList` | `src/components/cart/CartItemList.vue` | CartView |
| `CheckoutButton` | `src/components/cart/CheckoutButton.vue` | CartView |

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
| 2026-06-03 | YooKassa E2E тест проходит с тестовой картой (5555...4444). Обновлён checkout.spec.js. 96/96 E2E + 127 backend тестов зелёные. | e2e-tester |
| 2026-06-03 | CI/CD готов к YooKassa: `.env.example`, Helm values (test/prod), GitHub Actions e2e.yml обновлены. Test/prod secrets уже содержат YOOKASSA_SHOP_ID/SECRET_KEY (SOPS). | devops |
| 2026-06-02 | Создан PROJECT_CONTEXT.md | project-manager |
