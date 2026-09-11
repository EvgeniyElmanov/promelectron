# SESSION_START — работа с агентами Promelectron

> Всё работает через **навыки Kimi Code CLI** в `.kimi-code/skills/`.

## Язык

Когда пользователь общается на русском языке, основной агент и все субагенты должны рассуждать, думать и вести внутренний монолог на русском. Родительский агент должен явно сообщать субагентам, что исходный пользователь общается на русском языке. Финальные ответы пользователю должны быть на русском языке. Код, команды, идентификаторы, пути к файлам и технические термины остаются в оригинальном виде.

## Содержание

1. [Быстрый старт (первый раз)](#быстрый-старт-первый-раз)
2. [Ежедневный workflow](#ежедневный-workflow)
3. [Режимы работы](#режимы-работы)
4. [Формат задачи (5 элементов)](#формат-задачи-5-элементов)
5. [Роли и примеры задач](#роли-и-примеры-задач)
6. [После задачи](#после-задачи)
7. [Если что-то пошло не так](#если-что-то-пошло-не-так)
8. [Полезные файлы](#полезные-файлы)

## Быстрый старт (первый раз)

### Шаг 1: выбрать режим

| Если ты... | Используй |
|-----------|-----------|
| Не знаешь роль | [Workflow `/skill:implement`](#режим-a-полный-цикл-разработки-implement) |
| Нужно починить баг | [Workflow `/skill:fix`](#режим-b-исправление-бага-fix) |
| Знаешь точную роль | [Фиксированная роль](#режим-c-фиксированная-роль) |
| Нужно планирование/роадмап | [Project manager](#режим-d-project-manager) |

### Шаг 2: загрузить skill

Для любой задачи, когда не знаешь роль:
```
/skill:promelectron
Task: Add promo codes to cart
```

Для полного цикла разработки фичи:
```
/skill:implement "Add promo codes to cart"
```

Для бага:
```
/skill:fix "Race condition when adding to cart"
```

### Шаг 3: следовать за субагентом

Skill порождает субагентов (architect → developer → reviewer → QA). Одобри спецификацию, когда попросят, затем дай pipeline отработать.

## Ежедневный workflow

После загрузки workflow-навыка просто описывай задачи:

```
/skill:implement "Add a discount field to orders"
```

```
/skill:fix "Checkout button is disabled on mobile"
```

```
/skill:review
```

Skill автоматически направляет нужному субагенту.

## Режимы работы

### Режим A: полный цикл разработки `/skill:implement`

> Для задач, которым нужны проектирование, разработка, ревью и QA.

```
/skill:implement "Add promo codes to cart"
```

Как это работает:
1. **Architect** — анализ, вопросы, `spec.md` (plan mode; требует одобрения)
2. **Git worktree** — `.worktrees/implement-<task-id>` на ветке `feature/<task-id>`
3. **Backend dev** — model → schema → service → route → tests
4. **Frontend dev** — API → composable → component → page → tests
5. **Code review** — максимум 3 итерации
6. **QA / E2E** — pytest + vitest + Playwright
7. **Report** — merge только с явным одобрением

Флаги:
- `--quick` — пропустить фазу architect/spec
- `--backend-only` — только backend
- `--frontend-only` — только frontend

### Режим B: исправление бага `/skill:fix`

> Для багов: анализ → воспроизведение → фикс → тест.

```
/skill:fix "Race condition in cart add"
```

Как это работает:
1. Определяет роль из описания
2. Читает контекст и недавний git log
3. Воспроизводит баг (пишет минимальный тест)
4. Чинит причину, а не симптом
5. Запускает тесты
6. Проверяет golden path, если затронут

Флаги:
- `--backend` — явно backend-баг
- `--frontend` — явно frontend-баг
- `--infra` — инфраструктурный баг

### Режим C: фиксированная роль

> Если работаешь в одной роли весь день.

```
Role: backend-dev. Task: add email validation to registration.

Read PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, SESSION_LOG.md.
Load `/skill:backend-dev` (обёртка) or read `.agents/agents/backend-dev.md` and `.kimi-code/rules/pre-edit-checklist.md`.
After work update SESSION_LOG.md.
```

### Режим D: project manager

> Для планирования, приоритетов и роадмапа.

```
Role: project-manager. Task: prioritize backlog for next sprint.
```

## Работа через терминал

Полезные команды `make`:

```bash
make check       # lint + test
make status      # git + services
make dev         # запустить стек
make stop        # остановить стек
make test-backend
make test-frontend
make test-e2e
```

## Формат задачи (5 элементов)

Чем конкретнее задача, тем лучше результат.

```
[ROLE] Task: [one sentence]
File: [specific file or zone]
Related: [related files that will also change]
Do not break: [boundaries]
Verify: [how to confirm it works]
```

### Примеры

**Backend:**
```
[backend-dev] Task: add promo_code field to Order model
File: backend/src/app/models/order.py
Related: backend/src/app/schemas/order.py, backend/src/app/services/order_service.py
Do not break: existing migrations, payments table
Verify: pytest tests/test_orders.py && ruff check backend/src/app/models/order.py
```

**Frontend:**
```
[frontend-dev] Task: add promo code input to Cart.vue
File: frontend/src/views/Cart.vue
Related: frontend/src/services/cart.js, frontend/src/stores/cart.js
Do not break: existing total calculation, mobile layout
Verify: npm run test:unit Cart && check responsiveness (375px)
```

Подробнее в `.kimi-code/rules/prompt-format.md`.

## Роли и примеры задач

| Роль | Ключевые слова | Типичная задача | Пример |
|------|----------------|-----------------|--------|
| `backend-dev` | API, model, migration, service, endpoint, FastAPI, SQLAlchemy, pytest | Backend-модели, схемы, сервисы, роуты, тесты | "Add POST /promo/apply endpoint" |
| `frontend-dev` | Vue, component, page, form, Pinia, UI, CSS | Компоненты, сторы, composables, тесты | "Add promo input in Cart.vue" |
| `devops` | Docker, Helm, K8s, CI/CD, deploy, nginx, secret | Helm, Docker, CI/CD | "Add migration check to deploy.yml" |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click | Playwright-тесты | "Write checkout test with test card" |
| `code-reviewer` | review, code review, findings, quality | Код-ревью | "Review PR #42" |
| `security-reviewer` | security, audit, vulnerability, SQL injection | Security-аудит | "Audit API for SQL injection" |
| `project-manager` | plan, sprint, prioritize, backlog, estimate | Планирование, приоритеты, роадмап | "Estimate YooKassa integration timeline" |
| `architect` | design, architecture, spec, technical task, trade-off | Проектирование фич | "Design delivery integration" |
| `qa` | test, acceptance criteria, full check, qa | Полная проверка | "Check feature/X branch before merge" |

## После задачи

Агенты обновляют:

1. `docs/journal/session-log.md` — что сделано, изменённые файлы, риски
2. `docs/backlog.md` — статус задачи (если из спринта)
3. `docs/blockers.md` — новые блокеры (если появились)
4. `PROJECT_CONTEXT.md` — если архитектура изменилась

Перед отчётом:
- [ ] Тесты проходят (`make test`)
- [ ] Lint чистый (`make lint`)
- [ ] Критические пути из `.kimi-code/rules/golden-path.md` не сломаны

## Если что-то пошло не так

### Агент не следует ожидаемой роли

1. Перезагрузи workflow skill: `/skill:implement ...` или `/skill:fix ...`
2. Начни новую сессию Kimi CLI
3. Явно укажи роль: `Role: frontend-dev. Task: ...`

### Нужны две независимые задачи сразу

Не пиши: "Создай API и почини Helm"

Напиши два сообщения:
```
Task: create API for X
```
```
Task: fix Helm template for Y
```

## Полезные файлы

| Файл | Когда читать |
|------|--------------|
| `.kimi-code/rules/prompt-format.md` | Перед формулировкой задачи |
| `.kimi-code/rules/pre-edit-checklist.md` | Перед редактированием кода |
| `.kimi-code/rules/dependency-map.md` | Перед изменением файла |
| `.kimi-code/rules/golden-path.md` | Перед завершением |
| `.kimi-code/rules/task-template.md` | При создании нового пункта бэклога |
| `.kimi-code/skills/<role>/SKILL.md` | При работе в фиксированной роли |
| `.kimi-code/AGENTS.md` | Активный индекс инвариантов проекта и обзор системы агентов |
| `docs/guides/agent-routing.md` | Документация по маршрутизации |
| `PROJECT_CONTEXT.md` | В начале сессии — стек, статус, блокеры |
| `docs/backlog.md` | В начале сессии — текущий спринт |
| `docs/blockers.md` | В начале сессии — активные блокеры |
