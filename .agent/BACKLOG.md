# Бэклог Promelectron

**Версия:** 1.2
**Дата:** 2026-06-24
**Формат:** 1 спринт = 2 недели

---

## Текущий спринт: Sprint 1 (2026-06-01 — 2026-06-14)

| # | Задача | Агент | Приоритет | Статус | Зависимости | Оценка | Блокер |
|---|--------|-------|-----------|--------|-------------|--------|--------|
| 1 | Интеграция ЮKassa (реальные платежи) | backend-dev | P0 | **in_progress** | — | 2 недели | — |
| 1a | ЮKassa: SDK + конфиг + env vars | backend-dev | P0 | **done** ✅ | — | 1 день | — |
| 1b | ЮKassa: Alembic миграция Payment | backend-dev | P0 | **done** ✅ | 1a | 1 день | — |
| 1c | ЮKassa: YooKassaService (create/get payment) | backend-dev | P0 | **done** ✅ | 1a, 1b | 2 дня | — |
| 1d | ЮKassa: Обновить create_payment endpoint | backend-dev | P0 | **done** ✅ | 1c | 1 день | — |
| 1e | ЮKassa: Webhook endpoint + подпись | backend-dev | P0 | **done** ✅ | 1d | 2 дня | — |
| 1f | ЮKassa: Frontend редирект + success page | frontend-dev | P0 | **done** ✅ | 1d | 2 дня | — |
| 1g | ЮKassa: Backend тесты | backend-dev | P0 | **done** ✅ | 1e | 2 дня | — |
| 1h | ЮKassa: E2E тест с тестовой картой | e2e-tester | P0 | **done** ✅ | 1f, 1e | 2 дня | — |
| 2 | Webhook обработка платежей | backend-dev | P0 | **done** ✅ | #1 | 3 дня | — |
| 3 | Гостевая корзина: backend API | backend-dev | P0 | **done** ✅ | — | 1 неделя | — |
| 4 | Гостевая корзина: localStorage + merge при login | frontend-dev | P0 | **done** ✅ | #3 | 1 неделя | — |
| 5 | Убрать hardcoded secrets (SECRET_KEY, SEED_SECRET, docker-compose, Helm placeholders) | backend-dev + devops | P0 | **in_progress** | — | 2 дня | — |
| 6 | Исправить Helm worker templates (Celery command + enabled flag) | devops | P0 | **blocked** | — | 2 дня | BLK-001, BLK-002 |
| 7 | Подключить Sentry (backend + frontend) | devops | P0 | **in_progress** | — | 3 дня | — |
| 8 | Настроить backup БД (pg_dump → S3/MinIO) | devops | P0 | **in_progress** | — | 2 дня | — |
| 9 | E2E тесты гостевой корзины | e2e-tester | P0 | **done** ✅ | #3, #4 | 2 дня | — |
| 10 | Product.price → Numeric(10,2) + Alembic | backend-dev | P0 | todo | — | 2 дня | BLK-006 |
| 11 | OAuth Google ID — production настройка (credentials, redirect URI, валидация) | backend-dev + devops | P0 | **done** ✅ | — | 2 дня | — |
| 11a | Вписать GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET в `.env` и SOPS secrets | devops | P0 | **done** ✅ | #11 | 1 день | — |
| 12 | OAuth Yandex ID — production настройка (credentials, redirect URI, валидация) | backend-dev + devops | P0 | **done** ✅ | — | 2 дня | — |
| 13 | Исправить malformed revision ID в миграции `20260531_222559_guest_order_fields.py` | backend-dev | P0 | **in_progress** | — | 1 день | BLK-006 |
| 14 | Добавить `.dockerignore` в `backend/` | devops | P1 | todo | — | 1 день | — |
| 15 | Убрать `console.error` из production-кода фронтенда | frontend-dev | P2 | todo | — | 1 день | — |
| 16 | Написать unit-тесты для `useCart` composable | frontend-dev | P2 | todo | — | 2 дня | — |

**Цель спринта:** Реальные платежи работают, гостевая корзина в проде, OAuth production-ready, нет критичных security issues.

**Статус цели:** Частично выполнена. Гостевая корзина ✅. OAuth Yandex ✅, Google ✅. Security issues (hardcoded secrets) 🔄. Реальные платежи в работе. Исправление Alembic 🔄.

---

## Следующий спринт: Sprint 2 (2026-06-15 — 2026-06-28)

| # | Задача | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-----------|-------------|--------|
| 17 | Distributed rate limiting (Redis-backed SlowAPI) | backend-dev | P0 | — | 3 дня |
| 18 | Убрать Alembic из lifespan → только Helm hook | backend-dev | P0 | #6 | 1 день |
| 19 | Добавить Celery Beat в Helm (CronJob) | devops | P0 | #6 | 2 дня |
| 20 | PodSecurityContext + non-root в Helm | devops | P0 | #6 | 2 дня |
| 21 | Self-service onboarding продавцов (backend) | backend-dev | P1 | — | 2 недели |
| 22 | Self-service onboarding UI | frontend-dev | P1 | #21 | 1 неделя |
| 23 | Product variants (size/color/SKU matrix) backend | backend-dev | P1 | #10 | 2 недели |
| 24 | Product variants UI | frontend-dev | P1 | #23 | 1 неделя |
| 25 | E2E self-service onboarding | e2e-tester | P1 | #21, #22 | 2 дня |
| 26 | Перенести email/notification в Celery (async) | backend-dev | P1 | #6, #19 | 1 неделя |
| 27 | Добавить `state` nonce в OAuth flow | backend-dev | P2 | #11, #12 | 2 дня |
| 28 | Lazy loading для admin/supplier views | frontend-dev | P2 | — | 3 дня |
| 40 | Унифицировать хранение OAuth секретов: перенести Google/Yandex из GitHub Secrets в SOPS | devops | P2 | — | 1 день |
| 41 | [#15] Расширенные данные получателя: отчество для резидентов РФ, телефон и сохранение получателей | backend-dev + frontend-dev | P1 | — | 4 недели |

### Детальное описание задачи #15

**Проблема:** в корзине авторизованного пользователя форма получателя содержит только Имя и Фамилию, телефон не запрашивается. Для гостевого чекаута телефон есть, но хранится отдельно от получателя.

**Цель:** добавить телефон и опциональное отчество для резидентов РФ, вынести данные получателя в отдельную сущность `Recipient`, поддержать несколько сохранённых получателей и автозаполнение из профиля.

**Решения по open questions:**
- Резидентство РФ определяется по профилю пользователя (`User.country_code`, default `RU`). Для гостей — default `RU` с возможностью смены.
- В профиль добавляются отдельные поля `first_name`, `last_name`, `patronymic`, `country_code`.
- Реализация идёт поэтапно: MVP → Recipient v1 → Recipient v2.
- Миграция старых заказов выполняется на этапе Recipient v1; старые колонки остаются deprecated.
- Feature flag `recipient_v2` нужен только для третьего этапа.

**Этапы реализации:**
1. **MVP:** добавить `recipient_phone` и `recipient_patronymic` в `Order`, схемы, фронт, CDEK, админку.
2. **Recipient v1:** создать таблицу `recipients`, добавить `orders.recipient_id`, мигрировать старые заказы.
3. **Recipient v2:** несколько сохранённых получателей, CRUD в профиле, выбор в корзине, получатель по умолчанию.

**Acceptance Criteria:**
- Авторизованный пользователь видит в корзине поля получателя: Имя*, Фамилия*, Отчество (опционально для резидентов РФ), Телефон*.
- Гостевой чекаут запрашивает те же поля + страну (default РФ).
- Телефон валидируется по формату `+7XXXXXXXXXX` (фронт — маска, бэк — Pydantic).
- В админке заказа отображаются ФИО и телефон получателя.
- При создании заказа в CDEK передаются телефон и ФИО получателя.
- Все тесты проходят.

**Риски:**
- Миграция старых авторизованных заказов без телефона (fallback на `User.phone` или `NULL`).
- Парсинг существующих `full_name` при миграции профилей.
- Изменения в критичном пользовательском пути — чекаут.

---

## Бэклог Фазы 2 (Q3 2026)

| # | Задача | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-----------|-------------|--------|
| 29 | Sub-orders (разделение заказа по поставщикам) | backend-dev | P1 | #1 (платежи) | 4 недели |
| 30 | Комиссионная система + выплаты | backend-dev | P1 | #29 | 4 недели |
| 31 | Интеграция СДЭК / Почта России | backend-dev | P1 | — | 4 недели |
| 32 | Промо-система (купоны, акции, баннеры) backend | backend-dev | P1 | — | 3 недели |
| 33 | Промо-система UI | frontend-dev | P1 | #32 | 2 недели |
| 34 | Full-text search (PostgreSQL tsvector) | backend-dev | P1 | — | 3 недели |
| 35 | Возвраты и возмещения | backend-dev | P1 | #1 (платежи) | 3 недели |
| 36 | Pinia полный переход | frontend-dev | P1 | — | 2 недели |
| 37 | Модерация товаров и отзывов | backend-dev | P1 | — | 2 недели |
| 38 | Модерация UI | frontend-dev | P1 | #37 | 1 неделя |
| 39 | JWT refresh tokens + HttpOnly cookies | backend-dev + frontend-dev | P1 | — | 1 неделя |

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
| 3 | Гостевая корзина — backend API + merge endpoint | 2026-05-31 | `POST /cart/merge`, 123/123 backend тестов ✅ |
| 4 | Гостевая корзина — frontend + merge при login | 2026-05-31 | `useCart` composable, localStorage, 80/80 frontend тестов ✅ |
| 5 | E2E тесты гостевой корзины | 2026-05-31 | Обновлён `auth.spec.js`, CI/CD зелёный ✅ |
| 6 | OAuth Yandex ID — production настройка | 2026-05-31 | Backend endpoints + frontend UI, credentials из env |
| 7 | OAuth Google ID — production настройка | 2026-06-01 | Backend endpoints + frontend UI, credentials получены из env ✅ |
