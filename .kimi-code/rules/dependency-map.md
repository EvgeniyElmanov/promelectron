---
name: dependency-map
description: >
  Dependency map for Promelectron backend/frontend/infra changes.
type: prompt
disableModelInvocation: true
---

## Rule: dependency-map

> **Правило:** Если изменил файл в левой колонке — проверь/обнови файлы в правой колонке.  
> Это экономит время на поиск сломанных мест.
> Follow [Rule: Agent Commons](agent-commons.md) > Language Rule.

### Backend

#### Изменил Model (`backend/src/app/models/*.py`)
**Обнови:**
- `backend/src/app/schemas/*.py` — Pydantic схемы
- `backend/src/app/models/__init__.py` — экспорт модели
- `backend/src/app/db/` — base/metadata, если нужно
- Alembic миграция — `alembic revision --autogenerate -m "..."`
- `backend/src/app/services/*.py` — если использует модель
- `backend/tests/` — тесты на CRUD

**Пример:**
```
models/payment.py  →  schemas/payment.py
                   →  models/__init__.py
                   →  alembic revision
                   →  services/payment_service.py
                   →  tests/test_payments.py
```

#### Изменил Schema (`backend/src/app/schemas/*.py`)
**Обнови:**
- `backend/src/app/services/*.py` — если менял response/input
- `backend/src/app/api/*.py` — route handlers
- `frontend/src/api/*.js` — axios calls (если менялся API contract)

#### Изменил Service (`backend/src/app/services/*.py`)
**Обнови:**
- `backend/src/app/api/*.py` — routes используют service
- `backend/tests/` — unit-тесты сервиса
- `frontend/src/api/*.js` — если изменился return format

#### Изменил Route/API (`backend/src/app/api/*.py`)
**Обнови:**
- `backend/src/app/main.py` — `include_router` для нового роутера
- `backend/tests/` — API tests
- `frontend/src/api/*.js` — frontend API layer
- `frontend/src/views/*.vue` / `frontend/src/router/` — если добавилась страница
- `PROJECT_CONTEXT.md` — API Inventory
- E2E tests — если затронут пользовательский сценарий

#### Изменил Config (`backend/src/app/core/config.py`)
**Обнови:**
- `.env.example` — новые env vars
- `backend/.env.example` — новые env vars
- `backend/src/app/services/*.py` — если используют config
- Docker Compose / Helm — если новые переменные

### Frontend

#### Изменил Component (`frontend/src/components/*.vue`)
**Обнови:**
- `frontend/src/__tests__/` — vitest тесты
- `frontend/src/views/*.vue` — parent views
- `frontend/src/router/` — если добавляется новый route
- E2E tests — `data-testid` селекторы

#### Изменил Composable (`frontend/src/composables/*.js`)
**Обнови:**
- Все компоненты, которые `import` этот composable
- `frontend/src/__tests__/` — тесты composable

#### Изменил API layer (`frontend/src/api/*.js`)
**Обнови:**
- Компоненты/composables, использующие этот API call
- Если менялся endpoint path — проверь trailing slash
- `PROJECT_CONTEXT.md` — API Inventory

### Инфраструктура

#### Изменил Dockerfile / docker-compose.yml
**Обнови:**
- `backend/docker-entrypoint.sh`
- `scripts/run_dev.sh`, `scripts/stop_dev.sh`
- Helm charts (`infra/helm/`)
- `.dockerignore`

#### Изменил Helm chart (`infra/helm/`)
**Обнови:**
- `backend/src/app/core/config.py` — если новые env vars
- `.env.example`
- CI/CD pipeline (`.github/workflows/`)

#### Изменил `.github/workflows/`
**Проверь:**
- `make pre-push` проходит локально
- Секреты настроены в GitHub Secrets / SOPS

### Быстрый поиск зависимостей

```bash
# Кто использует мой модуль?
grep -r "PaymentService" backend/src/
grep -r "useCart" frontend/src/

# Где вызывается endpoint?
grep -r "createPayment\|usePayment" frontend/src/

# Какие тесты есть?
find backend/tests -name "*payment*"
find frontend/src/__tests__ -name "*Cart*"
```

---
