# 🤖 Kimi Agent System — Promelectron

> **Адаптация агентов под наш проект:** Vue 3 + FastAPI + PostgreSQL
>
> Папка `.kimi/` — адаптированная версия агентов под Kimi Code CLI.

## Команды

## Быстрый старт (только Kimi CLI, без bash)

> 📘 Подробное руководство — в [`HOWTO.md`](./HOWTO.md).

### Master Skill /promelectron (рекомендуется)

```
/promelectron
Задача: <описание задачи>
```

Загружает мастер-скилл проекта с полным реестром агентов, роутингом, workflow и правилами. Агент сам определит роль и будет работать по инструкциям.

### Workflow-скиллы (для сложных процессов)

```
/implement <описание фичи>     # полный цикл: архитектор → dev → review → QA → MR
/fix <описание бага>           # багфикс: анализ → воспроизведение → фикс → тест
/deploy <test|prod>            # деплой через GitHub Actions
/review [--security-only]      # code review текущих изменений
/context-sync                  # обновление PROJECT_CONTEXT.md и BACKLOG.md
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
| `architect` | Анализ, trade-offs, написание `spec.md` перед реализацией | `agents/architect.md` |
| `backend-dev` | FastAPI + SQLAlchemy + pytest | `agents/backend-dev.md` |
| `frontend-dev` | Vue 3 + Vitest | `agents/frontend-dev.md` |
| `code-reviewer` | Quality review | `agents/code-reviewer.md` |
| `e2e-tester` | Playwright E2E | `agents/e2e-tester.md` |
| `qa` | Оркестрация pytest + vitest + Playwright, проверка Acceptance Criteria | `agents/qa.md` |
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

| Skill | Описание | Команда |
|-------|----------|---------|
| `promelectron` | **Мастер-скилл.** Реестр агентов, роутинг, workflow, правила. Загружай всегда первым. | `/promelectron` |
| `implement` | Полный цикл разработки: архитектор → git branch → dev → review (max 3) → QA (max 2) → MR | `/implement` |
| `fix` | Багфикс workflow: анализ → воспроизведение → фикс → тест → golden path check | `/fix` |
| `deploy` | Деплой в test/prod через GitHub Actions + E2E smoke test | `/deploy` |
| `review` | Code review: security + quality + tests. Записывает findings в `.agent/REVIEW_FINDINGS.md` | `/review` |
| `context-sync` | Синхронизация PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md по реальному состоянию кода | `/context-sync` |
| `plan-maintainer` | Поддержка плана (BACKLOG.md, PLANNING_HANDOFF.md) | `/plan-maintainer` |

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

1. **Entry** — загружаем `/promelectron` (мастер-скилл) или workflow-скилл (`/implement`, `/fix`, etc.)
2. **Анализ** — читаем `PROJECT_CONTEXT.md`, `.agent/BACKLOG.md`, `.agent/BLOCKERS.md`
3. **Backend** — model → schema → service → route → tests
4. **Frontend** — API service → composable → component → page → route → tests
5. **Review** — security + quality checklist (через `/review`)
6. **Tests** — pytest + vitest + playwright
7. **Commit** — только после явного разрешения пользователя

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
