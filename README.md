# Promelectron

Интернет-магазин электротоваров на **FastAPI + Vue 3** с CI/CD через GitHub Actions → Harbor → Kubernetes.

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
    Entry(["/skill:*"])
    Entry --> Tracker

    Tracker["Tracker"]
    Tracker --> Worktree

    Worktree["git worktree<br/>.worktrees/{id}"]
    Worktree -.-> libs["libs"]
    Worktree -.-> best["best-pract"]
    Worktree -.-> code["codebase"]

    libs --> Architect
    best --> Architect
    code --> Architect

    Architect["Architect<br/><font color='#c62828'>⚠ plan mode required</font>"] <-.->|<i>прорабатывают архитектуру</i>| Human([Human])

    Architect --> Plan["PLAN.md"]
    Plan --> Approve{"auto / human<br/><i>approve?</i>"}
    Approve -.->|<font color='#c62828'>revise</font>| Plan
    Approve -->|<font color='#2e7d32'>approved</font>| Dev

    JiraCon["Jira / Confluence"] -.->|<i>spec context</i>| Architect
    Figma["Figma"] -.->|<i>design tokens</i>| Dev

    Dev --> SelfRev["Self-review<br/><i>adversarial audit diff</i>"]

    SelfRev --> Contract{"API contract<br/>backend ↔ frontend"}
    Contract -.->|<font color='#c62828'>расхождение</font>| Dev
    Contract -->|<font color='#2e7d32'>ok</font>| Reviewer

    Reviewer["Reviewer"] -->|<i>1-й проход & адаптивно к диффу</i>| Approved{APPROVED?}
    Reviewer -.->|<i>security-sensitive diff</i>| SecRev["security-reviewer"]
    SecRev --> Approved
    Approved -.->|<font color='#c62828'>нет</font>| Dev
    Approved -.->|<font color='#2e7d32'>да</font>| QA_Gate

    QA_Gate["QA Gate"] -->|<i>опционально · --qa</i>| MR

    MR["PR → GitHub"] --> KC["Knowledge Capture<br/><i>уроки → rules / skills / docs</i>"]
    KC --> Done([Done])

    noteBottom["re-review — один агент (шард при LARGE) · цикл до 3 итераций"]
    MR ~~~ noteBottom
    noteTrace["agent_state.py — trace.jsonl на границах фаз · correlation ID"]
    KC ~~~ noteTrace

    classDef entry fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,color:#424242
    classDef tracker fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#1565c0
    classDef worktree fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,stroke-dasharray:5 5,color:#2e7d32
    classDef research fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#6a1b9a
    classDef human fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px,color:#6a1b9a
    classDef dev fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#2e7d32
    classDef review fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#ef6c00
    classDef qa fill:#fffde7,stroke:#f9a825,stroke-width:2px,stroke-dasharray:5 5,color:#ef6c00
    classDef ship fill:#ffebee,stroke:#c62828,stroke-width:2px,color:#c62828
    classDef note fill:none,stroke:none,color:#616161

    class Entry entry
    class Tracker tracker
    class Worktree worktree
    class libs,best,code research
    class Architect human
    class Human human
    class Dev dev
    class Plan dev
    class Approve review
    class SelfRev dev
    class Contract review
    class Reviewer review
    class SecRev review
    class Approved review
    class QA_Gate qa
    class MR ship
    class KC ship
    class Done ship
    class JiraCon research
    class Figma research
    class noteBottom note
    class noteTrace note
```

Entry-скиллы:
- `/skill:implement` / `/skill:fix` → **Tracker**
- `/skill:spec` → **Architect**
- `/skill:review` → **Reviewer**
- `/skill:qa-gate` → **QA Gate**
- `/skill:ship` → **PR → GitHub**
- `/skill:flow-implement` / `/skill:flow-fix` / `/skill:flow-review` → **read-only статус** задачи (диаграмма с подсветкой текущей фазы)

Кубики пайплайна:

| Кубик | Роль | Что делает |
|-------|------|------------|
| Tracker | — | Определяет роль и маршрут задачи |
| Architect | `architect` | Пишет техническую спецификацию в plan mode |
| Research | `explore` subagents | Параллельный research: libraries, best-practices, codebase |
| Backend Dev | `backend-dev` | Модель → схема → сервис → эндпоинт → тесты |
| Frontend Dev | `frontend-dev` | API client → composable → компонент → страница → тесты |
| Plan | dev-роли | Пишет `$WORKTREE/PLAN.md` перед кодированием |
| Approve | оркестратор | Auto-одобрение простых планов / human-одобрение сложных |
| Self-review | dev-роли | Adversarial audit своего diff (3–5 проблем) до ревью |
| API Contract | оркестратор | Сверка backend ↔ frontend контракта до ревью (Step 5.5) |
| Code Reviewer | `code-reviewer` | Проверяет diff, пишет findings (Evidence / Impact / Action) |
| Security Reviewer | `security-reviewer` | Добавляется для auth/payments/orders/upload |
| QA | `qa` | Запускает pytest + vitest, проверяет Acceptance Criteria |
| E2E Tester | `e2e-tester` | Добавляет/обновляет Playwright-тесты |
| Ship | `ship` | Открывает PR, публикует H-items |
| Knowledge Capture | оркестратор | Уроки run → rules / skills / LESSONS_LEARNED (Step 8.5) |
| Trace | `agent_state.py` | trace.jsonl на границах фаз, correlation ID, детекция фазы |
| External sources | MCP | Jira/Confluence → spec context; Figma → design tokens |

Подробнее — в [`.kimi-code/AGENTS.md`](.kimi-code/AGENTS.md) и [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Пользователи по умолчанию (seed)

| Роль | Email | Пароль |
|------|-------|--------|
| Admin | `seed-admin@example.com` | `seedpassword123` |
| Supplier | `seed-supplier@example.com` | `seedpassword123` |

## Архитектура

Подробное описание архитектуры, соглашений и процессов разработки — в [`ARCHITECTURE.md`](ARCHITECTURE.md).
