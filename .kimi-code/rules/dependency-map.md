---
name: promelectron.rules.dependency-map
description: >
  Dependency map for Promelectron backend/frontend/infra changes.
type: prompt
disableModelInvocation: true
---

## Rule: dependency-map

> **Правило:** Если изменил файл в левой колонке — проверь/обнови файлы в правой колонке.  
> Это экономит время на поиск сломанных мест.

### Backend

#### Изменил Model (`backend/src/app/models/*.py`)
**Обнови:**
- `backend/src/app/schemas/*.py` — Pydantic схемы
- Alembic миграция — `alembic revision --autogenerate`
- `backend/src/app/services/*.py` — если использует модель
- `backend/tests/` — тесты на CRUD

**Пример:**
```
models/payment.py  →  schemas/payment.py
                   →  alembic revision
                   →  services/payment_service.py
                   →  tests/test_payments.py
```

#### Изменил Schema (`backend/src/app/schemas/*.py`)
**Обнови:**
- `backend/src/app/services/*.py` — если менял response/input
- `backend/src/app/api/*.py` — route handlers
- `frontend/src/api/*.js` — axios calls (если менялся API contract)
- `frontend/src/types/*.js` — JS-модули с контрактами данных / JSDoc-типами (если есть)

#### Изменил Service (`backend/src/app/services/*.py`)
**Обнови:**
- `backend/src/app/api/*.py` — routes используют service
- `backend/tests/` — unit-тесты сервиса
- `frontend/src/api/*.js` — если изменился return format

#### Изменил Route/API (`backend/src/app/api/*.py`)
**Обнови:**
- `backend/tests/` — API tests
- `frontend/src/api/*.js` — frontend API layer
- `frontend/src/views/*.vue` — если добавился новый endpoint
- `PROJECT_CONTEXT.md` — API Inventory

#### Изменил Config (`backend/src/app/core/config.py`)
**Обнови:**
- `.env.example` — новые env vars
- `backend/src/app/services/*.py` — если используют config
- Docker Compose / Helm — если новые переменные

### Frontend

#### Изменил Component (`frontend/src/components/*.vue`)
**Обнови:**
- `frontend/src/__tests__/` — vitest тесты
- `frontend/src/views/*.vue` — parent views
- E2E tests — `data-testid` селекторы

#### Изменил Composable (`frontend/src/composables/*.js`)
**Обнови:**
- Все компоненты, которые `import` этот composable
- `frontend/src/__tests__/` — тесты composable

#### Изменил Store / Pinia (`frontend/src/stores/*.js`)
**Обнови:**
- Все компоненты, использующие store
- `frontend/src/__tests__/` — store tests

#### Изменил API layer (`frontend/src/api/*.js`)
**Обнови:**
- Компоненты/composables, использующие этот API call
- Если менялся endpoint path — проверь trailing slash

### Инфраструктура

#### Изменил Dockerfile / docker-compose.yml
**Обнови:**
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
- `make test` проходит локально
- Секреты настроены в GitHub

### Быстрый поиск зависимостей

```bash
# Кто использует мой модуль?
grep -r "PaymentService" backend/src/
grep -r "useCart" frontend/src/

# Где вызывается endpoint?
grep -r "payments/" frontend/src/

# Какие тесты есть?
find backend/tests -name "*payment*"
find frontend/src/__tests__ -name "*Cart*"
```

---

