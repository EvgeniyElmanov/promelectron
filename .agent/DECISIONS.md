# Архитектурные решения Promelectron (ADR)

**Формат:** ADR-NNN
**Правило:** Каждое решение имеет ID, дату, контекст, альтернативы, статус и review date. Отклонённые идеи — внизу.

---

## Сводная таблица

| ID | Решение | Статус | Review | Related |
|----|---------|--------|--------|---------|
| ADR-001 | FastAPI + SQLAlchemy 2.0 async | ✅ Внедрено | 2026-12-01 | — |
| ADR-002 | Vue 3 + Vite + Axios | ✅ Внедрено | 2026-12-01 | — |
| ADR-003 | JWT Bearer + localStorage | ⚠️ Устарело | 2026-08-01 | TD-012 |
| ADR-004 | PostgreSQL + Alembic | ✅ Внедрено | 2026-12-01 | TD-010 |
| ADR-005 | Redis (кэш + rate limit) | ✅ Частично | 2026-08-01 | TD-009 |
| ADR-006 | MinIO + Local fallback | ✅ Внедрено | 2026-12-01 | — |
| ADR-007 | WebSocket для notifications | ✅ Внедрено | 2026-12-01 | TD-008 |
| ADR-008 | SELECT FOR UPDATE для stock | ✅ Внедрено | 2027-06-01 | — |
| ADR-009 | WebP image variants | ✅ Внедрено | 2026-12-01 | — |
| ADR-010 | Celery + Redis для background | ⚠️ Устарело — заменено на `job_worker` с таблицей `jobs` | 2026-08-01 | BLK-002 |
| ADR-011 | Mock payments (MVP) | ⚠️ Устарело | 2026-06-15 | BACKLOG #1 |
| ADR-012 | Composables вместо Pinia | ⚠️ Устарело | 2026-08-01 | TD-005 |
| ADR-013 | HttpOnly cookies + refresh tokens | 🔄 В бэклоге | 2026-09-01 | TD-012 |
| ADR-014 | PostgreSQL tsvector для search | 🔄 В бэклоге | 2026-10-01 | BACKLOG #24 |
| ADR-015 | ЮKassa как первый провайдер | 🔄 Sprint 1 | 2026-07-01 | BACKLOG #1 |

---

## Принятые решения

### ADR-001: FastAPI + SQLAlchemy 2.0 async
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Нужен async backend для высокой конкурентности |
| **Решение** | FastAPI + SQLAlchemy 2.0 async + asyncpg |
| **Альтернативы** | Django (слишком тяжёлый), Flask (нет async), Node.js (смена стека) |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2026-12-01 |
| **Related** | — |

### ADR-002: Vue 3 + Vite + Axios
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Современный reactive frontend |
| **Решение** | Vue 3 Composition API + Vite + Axios |
| **Альтернативы** | React (больше экосистема, но сложнее), Angular (слишком тяжёлый) |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | frontend-dev |
| **Review date** | 2026-12-01 |
| **Related** | — |

### ADR-003: JWT Bearer + localStorage
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Stateless auth для SPA |
| **Решение** | JWT Bearer, 30 мин expiry, хранение в localStorage |
| **Альтернативы** | Session cookies (stateful), OAuth-only (нет email auth) |
| **Статус** | ⚠️ Принято, но устарело — планируется миграция на HttpOnly cookies + refresh tokens (ADR-013) |
| **Owner** | backend-dev |
| **Review date** | 2026-08-01 |
| **Related** | TD-012 |

### ADR-004: PostgreSQL + Alembic
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | ACID БД для транзакционного интернет-магазина |
| **Решение** | PostgreSQL 16 + Alembic миграции |
| **Альтернативы** | MySQL (меньше фич), MongoDB (нет транзакций), CockroachDB (overkill) |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2026-12-01 |
| **Related** | TD-010 (Alembic в lifespan) |

### ADR-005: Redis (кэш + rate limit)
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Единое хранилище для кэша и rate limit |
| **Решение** | Redis 7 — кэш (TTL), rate limit (in-memory → Redis-backed) |
| **Альтернативы** | Memcached (только кэш), RabbitMQ (только очередь), Kafka (overkill) |
| **Статус** | ✅ Принято, внедрено частично — rate limit пока in-memory (TD-009) |
| **Owner** | backend-dev |
| **Review date** | 2026-08-01 |
| **Related** | TD-009 |

### ADR-006: MinIO + Local fallback для хранения
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Хранение изображений и файлов |
| **Решение** | MinIO (S3-compatible) + Local filesystem fallback через Storage Protocol |
| **Альтернативы** | AWS S3 (зависимость от облака), чисто local (не масштабируется) |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2026-12-01 |
| **Related** | — |

### ADR-007: WebSocket для real-time notifications
| | |
|---|---|
| **Дата** | 2024-Q2 |
| **Контекст** | Real-time уведомления пользователям |
| **Решение** | FastAPI WebSocket (`/ws/notifications`) + Redis pub/sub |
| **Альтернативы** | SSE (Server-Sent Events — проще, но однонаправленный), Firebase Cloud Messaging |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2026-12-01 |
| **Related** | TD-008 (side-effects в request thread) |

### ADR-008: SELECT FOR UPDATE для stock consistency
| | |
|---|---|
| **Дата** | 2024-Q2 |
| **Контекст** | Предотвращение race condition при одновременной покупке |
| **Решение** | `SELECT FOR UPDATE` на `Product.stock` при создании заказа |
| **Альтернативы** | Optimistic locking (версионирование), inventory service (микросервис — overkill) |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2027-06-01 |
| **Related** | — |

### ADR-009: WebP image variants (small/medium/large)
| | |
|---|---|
| **Дата** | 2024-Q2 |
| **Контекст** | Оптимизация изображений для разных устройств |
| **Решение** | Pillow генерация 3 вариантов WebP при загрузке |
| **Альтернативы** | On-the-fly resize (nginx image_filter, imgproxy), клиентская оптимизация |
| **Статус** | ✅ Принято, внедрено |
| **Owner** | backend-dev |
| **Review date** | 2026-12-01 |
| **Related** | — |

### ADR-010: Celery + Redis для background tasks
| | |
|---|---|
| **Дата** | 2026-05-28 |
| **Контекст** | Фоновая синхронизация с 1C ERP |
| **Решение** | Celery 5.3+ с Redis broker + beat scheduler |
| **Альтернативы** | APScheduler (проще, но меньше масштабируемость), cron (нет мониторинга), RQ (проще Celery) |
| **Статус** | ⚠️ Устарело — заменено на собственный `job_worker` с таблицей `jobs`. Код Celery удалён из backend, Docker Compose и Helm. |
| **Owner** | backend-dev |
| **Review date** | 2026-08-01 |
| **Related** | BLK-002 |

### ADR-011: Mock payments (этап MVP)
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Быстрый запуск без интеграции эквайринга |
| **Решение** | Mock payment service с генерацией `provider_payment_id` |
| **Альтернативы** | Сразу интегрировать ЮKassa (больше время до MVP) |
| **Статус** | ⚠️ Устарело — заменяется на реальные платежи (Sprint 1) |
| **Owner** | backend-dev |
| **Review date** | 2026-06-15 |
| **Related** | BACKLOG #1, #2 |

### ADR-012: Composables вместо Pinia (этап MVP)
| | |
|---|---|
| **Дата** | 2024-Q1 |
| **Контекст** | Простое состояние на старте проекта |
| **Решение** | Module-level reactive composables (useAuth, useToast) |
| **Альтернативы** | Pinia (больше boilerplate, но лучше для масштаба) |
| **Статус** | ⚠️ Устарело — планируется миграция на Pinia (TD-005) |
| **Owner** | frontend-dev |
| **Review date** | 2026-08-01 |
| **Related** | TD-005 |

### ADR-013: HttpOnly cookies + refresh tokens (планируется)
| | |
|---|---|
| **Дата** | 2026-05-30 |
| **Контекст** | JWT в localStorage уязвим к XSS |
| **Решение** | HttpOnly cookies для access + refresh tokens, sliding session |
| **Альтернативы** | Оставить localStorage (риск), OAuth-only (не покрывает email auth) |
| **Статус** | 🔄 Принято, в бэклоге |
| **Owner** | backend-dev |
| **Review date** | 2026-09-01 |
| **Related** | TD-012, ADR-003 |

### ADR-014: PostgreSQL tsvector для search (этап 1)
| | |
|---|---|
| **Дата** | 2026-05-30 |
| **Контекст** | Поиск ILIKE медленный на больших каталогах |
| **Решение** | PostgreSQL `tsvector` + GIN index для full-text search |
| **Альтернативы** | Elasticsearch (мощнее, но +инфраструктура), Meilisearch (проще), Algolia (платно) |
| **Статус** | 🔄 Принято, в бэклоге (Q3) |
| **Owner** | backend-dev |
| **Review date** | 2026-10-01 |
| **Related** | BACKLOG #24 |

### ADR-015: ЮKassa как первый платёжный провайдер
| | |
|---|---|
| **Дата** | 2026-05-30 |
| **Контекст** | Нужен реальный эквайринг для РФ |
| **Решение** | ЮKassa (ЮMoney) — REST API, webhooks, хорошая документация |
| **Альтернативы** | СберБанк (сложнее интеграция), Тинькофф (меньше документации), Stripe (не РФ) |
| **Статус** | 🔄 Принято, в Sprint 1 |
| **Owner** | backend-dev |
| **Review date** | 2026-07-01 |
| **Related** | BACKLOG #1, #2, ADR-011 |

---

## Отклонённые решения

| ID | Дата | Идея | Причина отклонения |
|----|------|------|-------------------|
| ADR-R001 | 2024-Q1 | GraphQL | Сложность, REST достаточен для текущих экранов |
| ADR-R002 | 2024-Q1 | Django | Слишком тяжёлый для API-first, FastAPI быстрее в разработке |
| ADR-R003 | 2024-Q1 | React | Vue 3 быстрее в разработке для команды, меньше boilerplate |
| ADR-R004 | 2024-Q2 | MongoDB | Нет ACID для финансовых транзакций, PostgreSQL надёжнее |
| ADR-R005 | 2024-Q2 | Firebase Auth | Зависимость от Google, нужна кастомная логика ролей |
| ADR-R006 | 2026-05-30 | Микросервисы сейчас | Монолит проще на 50% готовности, микросервисы — Фаза 3 |
| ADR-R007 | 2026-05-30 | Docker Swarm вместо K8s | K8s уже настроен в CI/CD, переход дороже поддержки |

---

## Шаблон нового ADR

```markdown
### ADR-NNN: Название
| | |
|---|---|
| **Дата** | YYYY-MM-DD |
| **Контекст** | 2-3 предложения |
| **Решение** | Что выбрали |
| **Альтернативы** | Что рассматривали и почему отклонили |
| **Статус** | 🔄 Принято / ✅ Внедрено / ⚠️ Устарело / ❌ Отклонено |
| **Owner** | backend-dev / frontend-dev / devops / project-manager |
| **Review date** | YYYY-MM-DD |
| **Related** | BACKLOG #X, TD-Y, BLK-Z |
```
