# Promelectron

Интернет-магазин (маркетплейс) на **FastAPI + Vue 3** с CI/CD через GitHub Actions → Harbor → Kubernetes.

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 16, Redis 7
- **Frontend:** Vue 3 (Composition API), Vite, Vue Router, Axios
- **Тесты:** pytest (backend), Vitest (frontend), Playwright (e2e)
- **База данных:** PostgreSQL, миграции через Alembic
- **Инфраструктура:** Docker Compose (local), Kubernetes + Helm (prod/test), Harbor (registry)
- **CI/CD:** GitHub Actions (self-hosted runner)

## Быстрый старт

```bash
# 1. Скопировать env
cp backend/.env.example backend/.env
# Отредактировать backend/.env при необходимости

# 2. Запустить всё
make dev

# 3. Наполнить тестовыми данными
make seed

# 4. Открыть приложение
# Frontend: http://localhost:5173
# API:       http://localhost:8000
# Docs:      http://localhost:8000/docs
```

## Команды (Makefile)

```bash
make dev              # Запуск backend + frontend + PostgreSQL + Redis
make stop             # Остановка dev-окружения
make seed             # Сид тестовых данных (admin, supplier, категории, товары)
make migrate          # Alembic upgrade head (через Docker)
make test             # Все тесты (pytest + vitest + e2e)
make test-backend     # pytest
make test-frontend    # Vitest
make test-e2e         # Playwright через Docker
```

## Структура проекта

```
backend/              — Бэкенд FastAPI
  src/app/
    api/              — REST эндпоинты
    models/           — SQLAlchemy ORM
    schemas/          — Pydantic схемы
    services/         — Бизнес-логика
  alembic/            — Миграции БД
  seed_data.py        — Сид тестовых данных
frontend/             — Фронтенд Vue 3
  src/
    views/            — Страницы
    components/       — Компоненты
    composables/      — Логика (useAuth и др.)
    router/           — Vue Router
    services/         — Axios API клиент
  e2e/                — Playwright E2E тесты
infra/helm/           — Helm чарты для Kubernetes
.github/workflows/    — CI/CD пайплайны
```

## API

Базовый URL: `http://localhost:8000/api/v1`

- `POST /register` — Регистрация
- `POST /login` — Логин
- `GET /products/` — Список товаров
- `GET /products/{id}` — Товар по ID
- `POST /cart/add` — Добавить в корзину
- `POST /orders/create` — Оформить заказ
- `GET /categories/` — Список категорий
- `GET /admin/dashboard` — Админ-дашборд (требует admin)
- ... (полный список в документации)

## Документация API

При запущенном бэкенде:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Окружения

| Окружение | URL | API |
|-----------|-----|-----|
| Local | http://localhost:5173 | http://localhost:8000 |
| Test | https://promelectron-test.aidrivencode.ru | https://api.promelectron-test.aidrivencode.ru |
| Prod | manual deploy | manual deploy |

## CI/CD Pipeline

```
push to main
    ↓
Build (Docker images) → Harbor
    ↓
Deploy to Test (K8s)
    ↓
Smoke tests (API + Frontend health)
    ↓
E2E tests (Playwright, 4 workers)
    ↓
Manual approval → Deploy to Prod
```

## AI Agent Pipeline

Проект использует мульти-агентный pipeline на базе **Kimi Code CLI**.  
Каждая задача проходит через изолированный git worktree, ролевых агентов, code review и QA gate.

> Источник диаграммы: [`docs/ai-agent-pipeline.mmd`](docs/ai-agent-pipeline.mmd)

```mermaid
%%{init: {'flowchart': {'curve': 'basis', 'padding': 20}}}%%
flowchart TD
    A(["/skill:implement"])
    R(["/skill:fix"])
    Q(["/skill:spec"])
    S(["/skill:review"])
    T(["/skill:qa-gate"])
    U(["/skill:ship"])

    A --> B
    R --> B

    B["Dispatcher<br/>role selection"] --> C
    C["Coordination plane<br/>.agent/runs/{task-id}/"] --> D
    D["Git worktree<br/>.worktrees/{task-id}/<br/>feature/{task-id}"] --> E
    E["Context check +<br/>retry policy"] --> F

    F["Research fan-out<br/>parallel subagents"] --> G
    G["Architect<br/>⚠ plan mode required<br/>writes spec.md"] --> H["   Human approval   "]
    G <-->|"needs clarification"| H
    H -->|"approved"| I

    I["GitHub Issue<br/>status: In progress"] --> J
    J["Developer"] --> K
    K["Reviewer"] --> L
    L{"APPROVED?"} -->|"нет"| J
    L -->|"да"| M

    M["QA Gate<br/>pytest + vitest + E2E"] --> N
    N["Pull Request<br/>GitHub<br/>status: In review"] --> O
    O["Human merge"] --> P["Done"]

    Q --> G
    S --> K
    T --> M
    U --> N

    classDef entry fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef coord fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef human fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef agent fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    classDef decision fill:#fffde7,stroke:#f9a825,stroke-width:2px
    classDef final fill:#ffebee,stroke:#c62828,stroke-width:2px

    class A,R,Q,S,T,U entry
    class C,D coord
    class H,O human
    class F,G,J,K,M,N agent
    class L decision
    class P final

    style H width:240px,height:80px
```

Кубики пайплайна:

| Кубик | Роль | Что делает |
|-------|------|------------|
| Dispatcher | — | Определяет роль для каждой задачи |
| Architect | `architect` | Пишет техническую спецификацию в plan mode |
| Research | `explore` subagents | Параллельный research: libraries, best-practices, codebase |
| Backend Dev | `backend-dev` | Модель → схема → сервис → эндпоинт → тесты |
| Frontend Dev | `frontend-dev` | API client → composable → компонент → страница → тесты |
| Code Reviewer | `code-reviewer` | Проверяет diff, пишет findings |
| Security Reviewer | `security-reviewer` | Добавляется для auth/payments/orders/upload |
| QA | `qa` | Запускает pytest + vitest, проверяет Acceptance Criteria |
| E2E Tester | `e2e-tester` | Добавляет/обновляет Playwright-тесты |
| Ship | `ship` | Открывает PR, публикует H-items |

Подробнее — в [`.kimi-code/AGENTS.md`](.kimi-code/AGENTS.md) и [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Пользователи по умолчанию (seed)

| Роль | Email | Пароль |
|------|-------|--------|
| Admin | `seed-admin@example.com` | `seedpassword123` |
| Supplier | `seed-supplier@example.com` | `seedpassword123` |

## Архитектура

Подробное описание архитектуры, соглашений и процессов разработки — в [`ARCHITECTURE.md`](ARCHITECTURE.md).
