# Бэклог Promelectron

**Версия:** 1.0
**Дата:** 2026-05-30
**Формат:** 1 спринт = 2 недели

---

## Текущий спринт: Sprint 1 (2026-06-01 — 2026-06-14)

| # | Задача | Агент | Приоритет | Статус | Зависимости | Оценка | Блокер |
|---|--------|-------|-----------|--------|-------------|--------|--------|
| 1 | Интеграция ЮKassa (реальные платежи) | backend-dev | P0 | **in_progress** | — | 2 недели | — |
| 2 | Webhook обработка платежей | backend-dev | P0 | todo | #1 | 3 дня | — |
| 3 | Гостевая корзина: backend API | backend-dev | P0 | **done** | — | 1 неделя | — |
| 4 | Гостевая корзина: localStorage + merge при login | frontend-dev | P0 | **done** | #3 | 1 неделя | — |
| 5 | Убрать hardcoded secrets (SECRET_KEY, SEED_SECRET) | backend-dev | P0 | todo | — | 2 дня | — |
| 6 | Исправить Helm worker templates (Celery) | devops | P0 | todo | — | 2 дня | .github/ защищена |
| 7 | Подключить Sentry | devops | P0 | todo | — | 3 дня | — |
| 8 | Настроить backup БД (pg_dump → S3/MinIO) | devops | P0 | todo | — | 2 дня | — |
| 9 | E2E тесты гостевой корзины | e2e-tester | P0 | **done** | #3, #4 | 2 дня | — |
| 10 | Product.price → Numeric(10,2) + Alembic | backend-dev | P0 | todo | — | 2 дня | — |
| 11 | OAuth Google ID — production настройка (credentials, redirect URI, валидация) | backend-dev + devops | P0 | todo | — | 2 дня | — |
| 12 | OAuth Yandex ID — production настройка (credentials, redirect URI, валидация) | backend-dev + devops | P0 | **done** | — | 2 дня | — |

**Цель спринта:** Реальные платежи работают, гостевая корзина в проде, OAuth production-ready, нет критичных security issues.

---

## Следующий спринт: Sprint 2 (2026-06-15 — 2026-06-28)

| # | Задача | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-----------|-------------|--------|
| 11 | Distributed rate limiting (Redis-backed) | backend-dev | P0 | — | 3 дня |
| 12 | Убрать Alembic из lifespan → только Helm hook | backend-dev | P0 | — | 1 день |
| 13 | PodSecurityContext + non-root в Helm | devops | P0 | #6 | 2 дня |
| 14 | Self-service onboarding продавцов | backend-dev | P1 | — | 2 недели |
| 15 | Self-service onboarding UI | frontend-dev | P1 | #14 | 1 неделя |
| 16 | Product variants (size/color/SKU matrix) backend | backend-dev | P1 | #10 | 2 недели |
| 17 | Product variants UI | frontend-dev | P1 | #16 | 1 неделя |
| 18 | E2E self-service onboarding | e2e-tester | P1 | #14, #15 | 2 дня |

---

## Бэклог Фазы 2 (Q3 2026)

| # | Задача | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-----------|-------------|--------|
| 19 | Sub-orders (разделение заказа по поставщикам) | backend-dev | P1 | #1 (платежи) | 4 недели |
| 20 | Комиссионная система + выплаты | backend-dev | P1 | #19 | 4 недели |
| 21 | Интеграция СДЭК / Почта России | backend-dev | P1 | — | 4 недели |
| 22 | Промо-система (купоны, акции, баннеры) backend | backend-dev | P1 | — | 3 недели |
| 23 | Промо-система UI | frontend-dev | P1 | #22 | 2 недели |
| 24 | Full-text search (PostgreSQL tsvector) | backend-dev | P1 | — | 3 недели |
| 25 | Возвраты и возмещения | backend-dev | P1 | #1 (платежи) | 3 недели |
| 26 | Pinia полный переход | frontend-dev | P1 | — | 2 недели |
| 27 | Lazy loading для admin/supplier views | frontend-dev | P1 | — | 1 неделя |
| 28 | Модерация товаров и отзывов | backend-dev | P1 | — | 2 недели |
| 29 | Модерация UI | frontend-dev | P1 | #28 | 1 неделя |

---

## Icebox (не запланировано)

### Growth
- Подписка на снижение цены
- Реферальная программа
- Программа лояльности (кэшбэк, баллы)
- Баннеры и реклама CPC

### Tech
- SSR / SSG (SEO)
- Elasticsearch (миграция с PostgreSQL tsvector)
- CDN + edge caching
- A/B тестирование

### Future
- Мобильное приложение (React Native / Flutter)
- Рекомендательная система (ML)
- Мультиязычность (i18n)
- Мультивалютность
- Event sourcing для заказов
- Микросервисная декомпозиция

---

## Завершённые

| ID | Задача | Дата | Результат |
|----|--------|------|-----------|
| 0 | Инициализация `.agent/` | 2026-05-30 | Создана структура памяти проекта |
| 1 | Восстановление деплоя после аудита | 2026-05-30 | Откат `3f88f3b`, rebuild из `3b51d2e`, CI/CD зелёный |
| 2 | Добавить `.dockerignore` в frontend | 2026-05-30 | Триггер CI/CD, уменьшен build context |
| 3 | Гостевая корзина — backend API + merge endpoint | 2026-05-31 | `POST /cart/merge`, 106/106 backend тестов ✅ |
| 4 | Гостевая корзина — frontend + merge при login | 2026-05-31 | `useCart` composable, localStorage, 80/80 frontend тестов ✅ |
| 5 | E2E тесты гостевой корзины | 2026-05-31 | Обновлён `auth.spec.js`, CI/CD зелёный ✅ |
