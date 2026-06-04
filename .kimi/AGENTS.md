# 🤖 Kimi Agent System — Promelectron

> **Адаптация агентов под наш проект:** Vue 3 + FastAPI + PostgreSQL
>
> Папка `.kimi/` — адаптированная версия агентов под Kimi Code CLI.

## Команды

## Быстрый старт (только Kimi CLI, без bash)

> 📘 Подробное руководство — в [`HOWTO.md`](./HOWTO.md).

### Auto-Orchestrator — всё сам (рекомендуется для начинающих)

```
Прочитай .agent/ORCHESTRATOR_PROMPT.md и следуй инструкциям.
Задача: <описание задачи>
```

Orchestrator сам определит роли и запустит изолированных Agent'ов. Никаких залипаний.

### Диспетчер — ручное переключение

```
Прочитай .agent/DISPATCHER_PROMPT.md и следуй инструкциям.
Задача: <описание задачи>
```

### Фиксированная роль

```
Роль: backend-dev. Задача: <описание задачи>
```

### Полная проверка проекта (через Makefile)

```bash
make auto MSG="<задача>"    # авто-режим: определит роли сам
make task MSG="<задача>"    # промпт с автоопределением роли
make ask MSG="<задача>"     # тоже, но с гарантированным сбросом роли
make check                   # lint + test
make status                  # git + tests + lint
```

## Агенты

| Агент | Назначение | Файл |
|-------|-----------|------|
| `orchestrator` | **Мета-агент:** авто-определение ролей, делегирование через Agent tool | `agents/orchestrator.md` |
| `dispatcher` | Автопереключение ролей при каждой задаче | `agents/dispatcher.md` |
| `backend-dev` | FastAPI + SQLAlchemy + pytest | `agents/backend-dev.md` |
| `frontend-dev` | Vue 3 + Vitest | `agents/frontend-dev.md` |
| `code-reviewer` | Quality review | `agents/code-reviewer.md` |
| `e2e-tester` | Playwright E2E | `agents/e2e-tester.md` |
| `integration-dev` | Dev-окружение | `agents/integration-dev.md` |
| `security-reviewer` | Security audit | `agents/security-reviewer.md` |
| `project-manager` | План, приоритеты, roadmap | `agents/project-manager.md` |
| `devops` | Инфраструктура, K8s, Helm, Docker, nginx | `agents/devops.md` |

## Rules

| Rule | Описание |
|------|----------|
| `security.md` | Security checklist (auth, injection, PII) |
| `git.md` | Git workflow (branch → PR → merge) |
| `planning.md` | Task format, status definitions, sprint boundaries |
| `agent-first.md` | Как работать с агентами в Kimi CLI |
| `pre-edit-checklist.md` | Проверки перед правкой кода |
| `golden-path.md` | Критичные сценарии, которые нельзя ломать |
| `dependency-map.md` | Связи между слоями (изменил X → проверь Y) |
| `task-template.md` | Шаблон задачи для агентов |
| `ai-self-check.md` | Правила для AI-ассистента (проверка фактов, diff) |

## Skills

| Skill | Описание |
|-------|----------|
| `add-feature` | Полный цикл добавления фичи |
| `plan-maintainer` | Поддержка плана (BACKLOG.md, PLANNING_HANDOFF.md) |
| `review` | Code review |
| `security-check` | Security audit |
| `auto-agent` | Автоматический выбор агента по задаче |

## Settings

`settings.json` — permissions + hooks:
- Deny: `rm -rf`, `git push --force`, `git reset --hard`, `DROP`
- Hook: `ruff check --fix` после каждого Edit/Write

## Стек проекта

| | Параметр | Значение |
|---|----------|----------|
| Backend path | `backend/` | FastAPI + SQLAlchemy 2.0 |
| Frontend | Vue 3 + JavaScript | Composition API, Vite |
| Package manager | `venv` | Python 3.12 |
| CI/CD | GitHub Actions → Harbor → K8s Helm | |

## Workflow

1. **Анализ** — читаем `.agent/DISPATCHER_PROMPT.md` или `PROJECT_CONTEXT.md`
2. **Backend** — model → schema → service → route → tests
3. **Frontend** — component → API integration → tests
4. **Review** — security + quality checklist
5. **Tests** — pytest + vitest + playwright
6. **Commit** — только после явного разрешения пользователя

## Обязательные файлы для чтения

Каждый агент в начале сессии:
- `PROJECT_CONTEXT.md` — актуальный стек, статус фич, блокеры, зависимости
- `.agent/BACKLOG.md` — текущий спринт
- `.agent/BLOCKERS.md` — активные блокеры
- Собственный `agents/<role>.md` — напоминание о зоне ответственности

После работы агент обновляет:
- `PROJECT_CONTEXT.md` — кратко: «Изменил X, теперь работает так»
- `.agent/tasks/TASK_XXX.md` — статус выполнения
- `.agent/BACKLOG.md` — если задача выполнена
