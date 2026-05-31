# Метрики Promelectron

**Версия:** 1.1
**Дата:** 2026-05-31
**Правило:** Обновляется каждую пятницу project-manager. AUDIT.md = статический снимок (раз в квартал), этот файл = живое состояние.

---

## Текущий спринт (Sprint 1)

### Delivery
| Метрика | Значение | Цель | Тренд |
|---------|----------|------|-------|
| Lead time (средний) | — | < 5 дней (P0), < 10 дней (P1) | — |
| Deployment frequency | — | > 2 раза в неделю | — |
| Change failure rate | — | < 5% | — |
| Mean time to recovery (MTTR) | — | < 2 часов | — |

### Качество
| Метрика | Значение | Цель | Тренд |
|---------|----------|------|-------|
| Backend test coverage | — | > 80% | — |
| Frontend test coverage | — | > 70% | — |
| E2E pass rate | 95/95 ✅ | 100% | → |
| Backend tests | 106/106 ✅ | 100% | ↑ |
| Frontend tests | 80/80 ✅ | 100% | ↑ |
| Bugs открыто | P0: 0, P1: 0, P2: 0 | P0: 0 | — |
| Bugs найдено в спринт | — | снижение | — |
| Code review turnaround | — | < 24 часов | — |

### Надёжность
| Метрика | Значение | Цель | Тренд |
|---------|----------|------|-------|
| Uptime test env | — | > 99.5% | — |
| Uptime prod env | — | > 99.9% | — |
| API p95 latency | — | < 200ms | — |
| Error rate | — | < 0.1% | — |

### Прогресс по блокам
| Блок | Было | Сейчас | Цель | Дельта |
|------|------|--------|------|--------|
| Покупатель | 55% | **58%** | 90% | ↑ |
| Продавец | 50% | 50% | 85% | — |
| Платформа | 40% | 40% | 80% | — |
| Инфраструктура | 55% | 55% | 90% | — |

---

## История по спринтам

| Спринт | Даты | Задач | Выполнено | Lead time | Coverage | Blockers | Deploys |
|--------|------|-------|-----------|-----------|----------|----------|---------|
| Sprint 0 | 2026-05-15 — 2026-05-30 | 5 | 5 | 3.2 дня | Backend: 75%, Frontend: 68% | 2 | 4 |
| Sprint 1 | 2026-06-01 — 2026-06-14 | 10 | **3** | — | Backend: 106, Frontend: 80 | 4 | 2 |

---

## Технический долг (живой список)

| ID | Модуль | Проблема | Приоритет | Оценка | План | Статус |
|----|--------|----------|-----------|--------|------|--------|
| TD-001 | `services/order_service.py` | 420 строк, SOLID нарушен | P2 | L (3-4 недели) | Split: OrderCreationService, OrderStatusService, OrderSideEffectHandler | в бэклоге |
| TD-002 | `views/Admin.vue` | 1317 строк, 5 табов в одном файле | P2 | M (2 недели) | Разбить на DashboardView, UsersView, CategoriesView, DeliveryView, OrdersView | в бэклоге |
| TD-003 | `services/product_service.py` | 218 строк, нет Repository layer | P2 | M (2 недели) | Внедрить ProductRepository, разделить query и command | в бэклоге |
| TD-004 | `models/product.py` | `price = Float` — ошибки округления | P0 | XS (2 дня) | Изменить на `Numeric(10,2)`, Alembic миграция | Sprint 1 |
| TD-005 | `frontend/src/` | Нет Pinia — ad-hoc composables | P2 | M (2 недели) | Миграция cart, favorites, auth на Pinia | в бэклоге |
| TD-006 | `frontend/src/router/index.js` | Нет lazy loading | P2 | XS (3 дня) | `() => import(...)` для admin/supplier views | в бэклоге |
| TD-007 | `api/orders.py` | Supplier lookup дублируется 7× | P2 | S (1 неделя) | Extract `get_current_supplier_record` dependency | в бэклоге |
| TD-008 | `services/*` | Side-effects в request thread | P2 | M (2 недели) | Перенести email/notification в Celery через event bus | в бэклоге |
| TD-009 | `utils/rate_limiter.py` | In-memory rate limiting | P0 | S (1 неделя) | Redis-backed SlowAPI | Sprint 1 |
| TD-010 | `main.py` | Alembic в lifespan (race condition) | P0 | XS (1 день) | Убрать из lifespan, оставить только Helm hook | Sprint 1 |
| TD-011 | `api/auth.py` | OAuth без state параметра | P2 | XS (2 дня) | Добавить `state` nonce | в бэклоге |
| TD-012 | `frontend/src/services/api.js` | JWT в localStorage | P2 | M (1 неделя) | HttpOnly cookies + refresh token flow | в бэклоге |
| TD-013 | `api/seed.py` | SEED_SECRET hardcoded | P0 | XS (2 дня) | Перенести в env var | Sprint 1 |
| TD-014 | `core/config.py` | SECRET_KEY weak default | P0 | XS (2 дня) | Убрать default, требовать env var | Sprint 1 |
| TD-015 | `frontend/nginx.conf` | Нет security headers | P2 | XS (1 день) | HSTS, X-Frame-Options, CSP | в бэклоге |

---

## Performance baseline

| Endpoint | p50 | p95 | p99 | Метод | Примечание |
|----------|-----|-----|-----|-------|------------|
| GET /api/v1/products/ | — | — | — | Cached (Redis) | 46x ускорение с кэшем |
| GET /api/v1/categories/ | — | — | — | Cached (Redis) | 1 мин TTL |
| POST /api/v1/orders/create | — | — | — | `SELECT FOR UPDATE` | Stock lock |
| POST /api/v1/payments/:id/confirm | — | — | — | Mock | Заменить на реальный |

**Цель:** Все p95 < 200ms после внедрения Pinia и Redis-backed rate limiting.

---

## Качество кода

| Метрика | Значение | Цель |
|---------|----------|------|
| Средняя сложность функции | — | < 10 |
| Дублирование кода | — | < 5% |
| Непокрытые модули | — | 0 |
| Ruff lint errors | 0 | 0 |
| Type coverage (mypy) | — | > 80% |
