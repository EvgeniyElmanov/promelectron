# Бэклог Promelectron

**Версия:** 1.4
**Дата:** 2026-08-28
**Формат:** 1 спринт = 2 недели

---

## Текущий спринт: Sprint 1 (2026-06-29 — 2026-07-12) — ЗАВЕРШЁН

> С 2026-07 работа идёт issue-driven: актуальные задачи и статусы — в разделе agent intake внизу файла и на GitHub Project board. Таблица ниже — историческая (закрытый Sprint 1).

| # | Задача | Issue | Агент | Приоритет | Статус | Зависимости | Оценка | Блокер |
|---|--------|-------|-------|-----------|--------|-------------|--------|--------|--------|
| 1 | Интеграция ЮKassa (реальные платежи) | | backend-dev | P0 | **in_progress** | — | 2 недели | — |
| 1a | ЮKassa: SDK + конфиг + env vars | | backend-dev | P0 | **done** ✅ | — | 1 день | — |
| 1b | ЮKassa: Alembic миграция Payment | | backend-dev | P0 | **done** ✅ | 1a | 1 день | — |
| 1c | ЮKassa: YooKassaService (create/get payment) | | backend-dev | P0 | **done** ✅ | 1a, 1b | 2 дня | — |
| 1d | ЮKassa: Обновить create_payment endpoint | | backend-dev | P0 | **done** ✅ | 1c | 1 день | — |
| 1e | ЮKassa: Webhook endpoint + подпись | | backend-dev | P0 | **done** ✅ | 1d | 2 дня | BLK-010 |
| 1f | ЮKassa: Frontend редирект + success page | | frontend-dev | P0 | **done** ✅ | 1d | 2 дня | — |
| 1g | ЮKassa: Backend тесты | | backend-dev | P0 | **done** ✅ | 1e | 2 дня | — |
| 1h | ЮKassa: E2E тест с тестовой картой | [#65](https://github.com/AutonomaCo/promelectron/issues/65) | e2e-tester | P0 | **done** ✅ | 1f, 1e | 2 дня | BLK-013 — E2E-карты flaky без реальных ключей; production-код оставлен, PR #95 заморожен |
| 2 | Webhook обработка платежей | | backend-dev | P0 | **done** ✅ | #1 | 3 дня | BLK-010 |
| 3 | Гостевая корзина: backend API | | backend-dev | P0 | **done** ✅ | — | 1 неделя | — |
| 4 | Гостевая корзина: localStorage + merge при login | | frontend-dev | P0 | **done** ✅ | #3 | 1 неделя | — |
| 5 | Убрать hardcoded secrets (SECRET_KEY, SEED_SECRET, docker-compose, Helm placeholders) | | backend-dev + devops | P0 | **done** ✅ | — | 2 дня | — |
| 6 | Удалить Celery worker из Helm, оставить `job-worker` deployment | | devops | P0 | **done** ✅ | — | 2 дня | — |
| 7 | Подключить Sentry (backend + frontend) | | devops | P0 | **in_progress** | — | 3 дня | — |
| 8 | Настроить backup БД (pg_dump → S3/MinIO) | | devops | P0 | **in_progress** | — | 2 дня | — |
| 9 | E2E тесты гостевой корзины | | e2e-tester | P0 | **done** ✅ | #3, #4 | 2 дня | — |
| 10 | Product.price → Numeric(10,2) + Alembic | | backend-dev | P0 | todo | — | 2 дня | — |
| 11 | OAuth Google ID — production настройка (credentials, redirect URI, валидация) | | backend-dev + devops | P0 | **done** ✅ | — | 2 дня | — |
| 11a | Вписать GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET в `.env` и SOPS secrets | | devops | P0 | **done** ✅ | #11 | 1 день | — |
| 12 | OAuth Yandex ID — production настройка (credentials, redirect URI, валидация) | | backend-dev + devops | P0 | **done** ✅ | — | 2 дня | — |
| 13 | Исправить malformed revision ID в миграции `20260531_222559_guest_order_fields.py` | | backend-dev | P0 | **done** ✅ | — | 1 день | — |
| 14 | Добавить `.dockerignore` в `backend/` | | devops | P1 | todo | — | 1 день | — |
| 15 | Убрать `console.error` из production-кода фронтенда | | frontend-dev | P2 | todo | — | 1 день | — |
| 16 | Написать unit-тесты для `useCart` composable | | frontend-dev | P2 | todo | — | 2 дня | — |
| 43 | Подключить реальный SMTP и отправку email + верификацию email при регистрации (BLK-005) | [#19](https://github.com/AutonomaCo/promelectron/issues/19) | backend-dev + frontend-dev + devops | P0 | **done** ✅ | — | 6 дней | — |

**Цель спринта:** Реальные платежи работают, гостевая корзина в проде, OAuth production-ready, нет критичных security issues.

**Статус цели:** Частично выполнена. Гостевая корзина ✅. OAuth Yandex ✅, Google ✅. Security issues (hardcoded secrets) ✅. Реальные платежи в работе. Sentry и backup БД 🔄.

### Детальное описание задачи #43

**Проблема:** В проекте реализована отправка email-уведомлений (`EmailService`), но в test/prod отсутствуют реальные SMTP-креды. Из-за этого все письма (welcome email после гостевого чекаута, сброс пароля, подтверждение заказа, обновление статуса) остаются в fallback-режиме: `EmailService` просто делает тихий `return`, письмо не отправляется и не логируется.

**Цель:** Подключить реальный SMTP-провайдер к test- и (по возможности) prod-окружению, обеспечить корректную передачу кредов через env / SOPS / GitHub Secrets, поддержать разные режимы шифрования (STARTTLS / SSL-TLS) и оставить безопасный fallback на логирование при отсутствии конфигурации.

**Окружения:**
- **test** — обязательно (`promelectron-test.aidrivencode.ru`).
- **prod** — желательно, если будут предоставлены отдельные креды (`promelectron.aidrivencode.ru`).

**Что нужно сделать:**
1. **Backend (`backend/src/app/core/config.py` + `backend/src/app/services/email_service.py`):**
   - Добавить `SMTP_FROM_NAME` и `SMTP_STARTTLS` в `Settings`.
   - Поддержать оба режима шифрования: `start_tls` (порт 587) и `use_tls` / SSL-TLS (порт 465).
   - Сформировать поле `From:` как `"{SMTP_FROM_NAME} <{SMTP_FROM}>"`.
   - Реализовать fallback: если `SMTP_USER` или `SMTP_PASSWORD` не заданы, логировать тему и получателя письма вместо тихого skip.
2. **Env-шаблоны:**
   - Обновить корневой `.env.example` и `backend/.env.example`: добавить `SMTP_FROM_NAME=` и `SMTP_STARTTLS=true` (по умолчанию), сохранить `SMTP_TLS=true` для обратной совместимости.
3. **Helm:**
   - Обновить `infra/helm/values.yaml`: в `env.open` добавить `SMTP_FROM_NAME` и `SMTP_STARTTLS`; оставить `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_TLS`.
   - Обновить `infra/helm/stage/test/values.yaml` и `infra/helm/stage/prod/values.yaml` при необходимости.
   - Добавить `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_NAME` (если чувствительно) в SOPS-encrypted `infra/helm/stage/test/secrets.yaml` и `infra/helm/stage/prod/secrets.yaml`.
4. **CI/CD:**
   - Обновить `.github/workflows/deploy.yml`: добавить `OVR_SMTP_USER`, `OVR_SMTP_PASSWORD`, `OVR_SMTP_FROM_NAME` (опционально) в список `--set-string env.secrets.*` overrides для test и prod.
5. **Тесты:**
   - Добавить/обновить unit-тесты `EmailService` с моком `aiosmtplib.send` для STARTTLS и SSL-TLS.
   - Проверить fallback-логирование при отсутствии кредов.
6. **Ручная проверка на test (после получения кредов):**
   - Гостевой чекаут с реальным email → после оплаты должен прийти welcome email с темой «Спасибо за заказ / ваш аккаунт создан».
   - Проверить логи backend: `SMTPSenderRefused` / `Timeout` не должно быть.
   - Убедиться, что письмо не в спаме.
7. **DNS (отложено до появления доступа):**
   - Настроить SPF, DKIM, DMARC для домена отправителя.

**Acceptance Criteria:**
- В `backend/src/app/core/config.py` есть `SMTP_FROM_NAME` и `SMTP_STARTTLS`.
- `EmailService` поддерживает STARTTLS (587) и SSL-TLS (465) в зависимости от `SMTP_TLS`/`SMTP_STARTTLS`.
- `.env.example` и Helm values содержат все SMTP-переменные (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, `SMTP_TLS`, `SMTP_STARTTLS`).
- Креды test-окружения записаны в SOPS-encrypted `infra/helm/stage/test/secrets.yaml` (и/или GitHub Secrets).
- Креды prod-окружения записаны в SOPS-encrypted `infra/helm/stage/prod/secrets.yaml` (и/или GitHub Secrets), если креды предоставлены.
- `.github/workflows/deploy.yml` прокидывает SMTP-переменные в Helm.
- При отсутствии `SMTP_USER`/`SMTP_PASSWORD` письмо не падает с ошибкой, а логируется (fallback).
- На test-окружении после гостевого чекаута приходит welcome email.
- Backend- и frontend-тесты проходят.

**Out of Scope:**
- Полный отказ от fallback-режима (fallback на логирование остаётся для dev/local).
- Перенос отправки email в `job_worker` (это задача #26 Sprint 2).
- Настройка SPF/DKIM/DMARC (выполняется отдельно при появлении доступа к DNS).
- Смена SMTP-провайдера после внедрения (будет отдельной задачей при необходимости).

**Риски:**
- Для Gmail/Yandex нужен app password, а не основной пароль — важно не скомпрометировать основную учётную запись.
- Без SPF/DKIM/DMARC письма могут попадать в спам.
- Если креды для prod не будут предоставлены, prod останется в fallback-режиме.
- Изменения в `EmailService` могут затронуть существующие тесты (mock `aiosmtplib.send`).

**Зависимости:**
- BLK-005 — получение реальных SMTP-кредов от пользователя.
- Доступ к SOPS/GPG для перешифрования `secrets.yaml`.
- Доступ к GitHub Secrets для добавления `SMTP_USER`, `SMTP_PASSWORD`.

---

## Следующий спринт: Sprint 2 (2026-06-15 — 2026-06-28)

| # | Задача | Issue | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-------|-----------|-------------|--------|
| 17 | Distributed rate limiting (Redis-backed SlowAPI) | | backend-dev | P0 | — | 3 дня |
| 18 | Убрать Alembic из lifespan → только Helm hook | | backend-dev | P0 | #6 | 1 день |
| 19 | Добавить CronJob для периодических 1C/jobs задач (заменяет Celery Beat) | | devops | P0 | #6 | 2 дня |
| 20 | PodSecurityContext + non-root в Helm | | devops | P0 | #6 | 2 дня |
| 21 | Self-service onboarding продавцов (backend) | | backend-dev | P1 | — | 2 недели |
| 22 | Self-service onboarding UI | | frontend-dev | P1 | #21 | 1 неделя |
| 23 | Product variants (size/color/SKU matrix) backend | | backend-dev | P1 | #10 | 2 недели |
| 24 | Product variants UI | | frontend-dev | P1 | #23 | 1 неделя |
| 25 | E2E self-service onboarding | | e2e-tester | P1 | #21, #22 | 2 дня |
| 26 | Перенести email/notification в `job_worker` (async) | | backend-dev | P1 | #6, #19 | 1 неделя |
| 27 | Добавить `state` nonce в OAuth flow | | backend-dev | P2 | #11, #12 | 2 дня |
| 28 | Lazy loading для admin/supplier views | | frontend-dev | P2 | — | 3 дня |
| 40 | Унифицировать хранение OAuth секретов: перенести Google/Yandex из GitHub Secrets в SOPS | | devops | P2 | — | 1 день |
| 41 | [#15] Расширенные данные получателя: отчество для резидентов РФ, телефон и сохранение получателей | | backend-dev + frontend-dev | P1 | — | 4 недели |

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

| # | Задача | Issue | Агент | Приоритет | Зависимости | Оценка |
|---|--------|-------|-------|-----------|-------------|--------|
| 29 | Sub-orders (разделение заказа по поставщикам) | | backend-dev | P1 | #1 (платежи) | 4 недели |
| 30 | Комиссионная система + выплаты | | backend-dev | P1 | #29 | 4 недели |
| 31 | Интеграция СДЭК / Почта России | | backend-dev | P1 | — | 4 недели |
| 32 | Промо-система (купоны, акции, баннеры) backend | | backend-dev | P1 | — | 3 недели |
| 33 | Промо-система UI | | frontend-dev | P1 | #32 | 2 недели |
| 34 | Full-text search (PostgreSQL tsvector) | | backend-dev | P1 | — | 3 недели |
| 35 | Возвраты и возмещения | | backend-dev | P1 | #1 (платежи) | 3 недели |
| 36 | Pinia полный переход | | frontend-dev | P1 | — | 2 недели |
| 37 | Модерация товаров и отзывов | | backend-dev | P1 | — | 2 недели |
| 38 | Модерация UI | | frontend-dev | P1 | #37 | 1 неделя |
| 39 | JWT refresh tokens + HttpOnly cookies | | backend-dev + frontend-dev | P1 | — | 1 неделя |

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

---

## GitHub Issues (agent intake)

Задачи, созданные агентом через `/skill:implement` и автоматически опубликованные в GitHub backlog.

| task-id | Issue | Title | Date |
|---------|-------|-------|------|
| — | [#5](https://github.com/AutonomaCo/promelectron/issues/5) | Кнопка «Отменить заказ» для пользователя | — |
| task-0703 | [#54](https://github.com/AutonomaCo/promelectron/issues/54) | Проверить формат даты и времени | 2026-07-03 |
| — | [#61](https://github.com/AutonomaCo/promelectron/issues/61) | Technical Specification: cart-select-items-for-payment | 2026-07-01 |
| — | [#63](https://github.com/AutonomaCo/promelectron/issues/63) | Technical Specification: fix-avatar-upload-notification | 2026-07-02 |
| yookassa-test-card-scenarios | [#65](https://github.com/AutonomaCo/promelectron/issues/65) | ЮKassa: покрытие тестовыми сценариями банковских карт (test mode) | 2026-07-06 |
| yookassa-card-test-coverage-65-follow-up | [#91](https://github.com/AutonomaCo/promelectron/issues/91) | fix(#65): follow-up fixes for YooKassa test-card coverage | 2026-07-14 |
| — | [#66](https://github.com/AutonomaCo/promelectron/issues/66) | Specification: onec-integration | 2026-07-07 |
| fix-rate-limit-register-login-crash | [#75](https://github.com/AutonomaCo/promelectron/issues/75) | Spec: fix-rate-limit-register-login-crash | 2026-07-12 |
| fix-avatar-upload-kubernetes | [#77](https://github.com/AutonomaCo/promelectron/issues/77) | Writable `/app/uploads` for avatar upload in Kubernetes | 2026-07-12 |
| — | Technical Specification: yookassa-e2e-ui-kassa-failed-3ds-0715 | [#96](https://github.com/AutonomaCo/promelectron/issues/96) | — | P1 | **done** (PR #97; ревизия 2026-08-26) | — | — | — |
| — | Technical Specification: admin-orders-date-cancel | [#104](https://github.com/AutonomaCo/promelectron/issues/104) | — | P1 | **done** (PR #106; ревизия 2026-08-26) | — | — | — |
| — | Technical Specification: admin-cancel-followups (--quick) | [#107](https://github.com/AutonomaCo/promelectron/issues/107) | — | P1 | **done** (PR #108; ревизия 2026-08-26) | — | — | — |
| — | Bug Spec: fix-e2e-auth-after-guest-checkout | [#112](https://github.com/AutonomaCo/promelectron/issues/112) | — | P1 | **done** (PR #113; ревизия 2026-08-26) | — | — | — |
| — | Technical Specification: catalog-filter-panel-122 | [#134](https://github.com/AutonomaCo/promelectron/issues/134) | — | P1 | **done** (PR #135, #136; ревизия 2026-08-26) | — | — | — |
| — | Спецификация: search-api-followups-0801 (#137, #138) | [#137](https://github.com/AutonomaCo/promelectron/issues/137) | — | P1 | **done** (PR #140; ревизия 2026-08-26) | — | — | — |
| — | Spec: fix-uploads-cache-onec | [#158](https://github.com/AutonomaCo/promelectron/issues/158) | — | P1 | **done** (PR #159) | — | — | — |
| — | Spec: feat-out-of-stock-ui | [#163](https://github.com/AutonomaCo/promelectron/issues/163) | — | P1 | **closed** — PDP через #165/#167, ProductCard → #176 | — | — | — |
| — | feat: бейдж «Нет в наличии» в карточке товара (stock=0) | [#176](https://github.com/AutonomaCo/promelectron/issues/176) | — | P1 | **done** (PR #181) | — | — | — |
| — | restore: cart-select-items-for-payment — фича #61 откачена в `41a5043`, восстановить из `fe6f0f9` | [#177](https://github.com/AutonomaCo/promelectron/issues/177) | 2026-08-26 | P1 | **done** (PR #178, merge `1569056`) | — | — | — |
| — | fix(uploads): MinIO-ветка serve_upload ловит только FileNotFoundError | [#160](https://github.com/AutonomaCo/promelectron/issues/160) | — | P1 | **done** (PR #180) | — | — | — |
| — | fix(tests): test_seed_catalog_script.py падает в Docker | [#161](https://github.com/AutonomaCo/promelectron/issues/161) | — | P1 | **done** (PR #180) | — | — | — |
| — | feat(onec): проверка X-1C-Checksum на /onec/intake/ | [#162](https://github.com/AutonomaCo/promelectron/issues/162) | — | P1 | **done** (PR #180) | — | — | — |
| — | fix(infra): make test-e2e, concurrency в deploy.yml, автоподготовка frontend-deps в worktree | [#179](https://github.com/AutonomaCo/promelectron/issues/179) | 2026-08-27 | P1 | **done** (PR #182) | — | — | — |
| — | tech-debt: привести alembic check в зелёное состояние (pre-existing schema/model drift) | [#183](https://github.com/AutonomaCo/promelectron/issues/183) | 2026-08-27 | P1 | **done** (PR #184, merge `46116cb`) | — | — | — |
| — | ci: добавить alembic check (make migrate-check) в CI workflow | [#185](https://github.com/AutonomaCo/promelectron/issues/185) | 2026-08-27 | P1 | **in review** (PR #187) | — | — | — |
| — | fix(e2e): флаки cart-select.spec.js — протечка состояния корзины между тестами | [#186](https://github.com/AutonomaCo/promelectron/issues/186) | 2026-08-27 | P1 | **backlog** | — | — | — |
| — | Spec: mobile-medium-fixes — пачка medium-фиксов мобильной версии | [#171](https://github.com/AutonomaCo/promelectron/issues/171) | — | P1 | **done** (PR #173) | — | — | — |
| — | Bug Spec: Избранное — удаление не работает + заливка сердечка | [#188](https://github.com/AutonomaCo/promelectron/issues/188) | — | P1 | **backlog** | — | — | — |
| fix-cdek-tracking-number | Bug Spec: fix-cdek-tracking-number | [#190](https://github.com/AutonomaCo/promelectron/issues/190) | 2026-08-28 | P1 | **done** (PR #191, merge `dfc1c83`) | — | — | — |
| — | Spec: toast-follow-scroll | [#194](https://github.com/AutonomaCo/promelectron/issues/194) | — | P1 | **backlog** | — | — | — |
| fix-cdek-order-number-collision | fix(cdek): уникальный номер заказа ИМ PM-{id}-{suffix} — коллизия после reseed БД | [#195](https://github.com/AutonomaCo/promelectron/issues/195) | 2026-08-29 | P1 | **done** (PR #197, merge `75f5850`) | — | — | — |
| — | Bug Spec: fix-order-emails | [#199](https://github.com/AutonomaCo/promelectron/issues/199) | — | P1 | **backlog** | — | — | — |
| fix-order-emails | fix(email): дубль письма «Заказ оформлен» при оплате + нет трек-номера в письме «Отправлен» | [#199](https://github.com/AutonomaCo/promelectron/issues/199) | 2026-08-29 | P1 | **done** (PR #200, merge `232fc35`) | — | — | — |
