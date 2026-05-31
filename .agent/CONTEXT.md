# Контекст проекта Promelectron

## Последняя сессия
- **Дата:** 2026-05-30
- **Что делали:** Восстановление деплоя после инцидента с аудитом
- **Результат:** Деплой восстановлен, `.agent/` расширена системой памяти

## Текущий фокус
- **Модуль:** Инфраструктура / Стабилизация после аудита
- **Статус:** Разблокировано, готовность к Sprint 1
- **% готовности:** ~50% (MVP+ с базовой функциональностью)

## Что уже сделано
- [x] Создана структура `.agent/` (BACKLOG, BLOCKERS, DECISIONS, METRICS, AGENTS)
- [x] Деплой frontend восстановлен (`.dockerignore` → rebuild из `3b51d2e`)
- [x] Найден корневой баг: `3f88f3b` (`USER nginx` без writable temp dirs)
- [x] Git откачен до стабильного `3b51d2e`
- [x] Все тесты зелёные: Backend 102/102 ✅, Frontend 77/77 ✅, E2E 95/95 ✅

## Что следующее (приоритет)
1. **Закрыть инцидент:** Обновить BLOCKERS.md, зафиксировать постмортем
2. **Sprint 1:** ЮKassa (реальные платежи) + Гостевая корзина
3. **Инфра:** Убрать hardcoded secrets, Sentry, backup БД
4. **Повторный аудит:** Безопасно применить security patches по одному

## Архитектура проекта
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 async, PostgreSQL 16, Redis 7, MinIO, Celery
- **Frontend:** Vue 3 + Vite, nginx:alpine (runtime)
- **Infra:** Docker, K8s Helm, GitHub Actions self-hosted runner → Harbor
- **API:** REST, WebSocket для real-time notifications
- **Auth:** JWT Bearer + localStorage (планируется HttpOnly cookies + refresh tokens)

## Важные решения
- Alembic миграции при старте приложения (планируется перенос в Helm hook)
- `SELECT FOR UPDATE` для консистентности stock
- MinIO + Local fallback для хранения файлов
- Mock payments → заменяются на ЮKassa в Sprint 1

## Известные проблемы
- **BLK-001:** `.github/` защищена — CI/CD правки требуют ручного доступа (P1)
- **BLK-002:** Celery worker отключён в Helm (`worker.enabled=false`) (P0)
- **BLK-003:** Frontend Dockerfile с `USER nginx` — rollout timed out (P0) → **РЕШЁН**
- **BLK-004:** `API_BASE_URL` в K8s test не настроен (P1)
- **BLK-005:** Нет реальных SMTP кредов — email в fallback (P1)

## Как запускать проект

```bash
# Backend (с БД и Redis)
cd backend && make dev-backend

# Frontend (dev server)
cd frontend && npm run dev

# Полный стек (Docker Compose)
make dev

# Tests
make test          # backend + frontend
make test-e2e      # Playwright
```

## Ссылки
- **План:** [PLANNING_HANDOFF.md](./PLANNING_HANDOFF.md) (единственный актуальный) + [BACKLOG.md](./BACKLOG.md)
- [Аудит проекта](/AUDIT.md)
- [Архитектура](/ARCHITECTURE.md)

