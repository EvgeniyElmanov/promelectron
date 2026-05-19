# 🤖 Kimi Agent System — My Shop

> **Адаптация агентов под наш проект:** Vue 3 + FastAPI + PostgreSQL
> 
> Оригинальная система агентов находится в `.claude/` (Claude Code format).
> Эта папка `.kimi/` — адаптированная версия под наш стек.

## Команды

```bash
# Code review текущих изменений
make review

# Security audit
make review-security

# Полная проверка
make check        # lint + test + review

# Статус проекта
make status       # git + tests + lint
```

## Агенты

| Агент | Назначение | Файл |
|-------|-----------|------|
| `backend-dev` | FastAPI + SQLAlchemy + pytest | `agents/backend-dev.md` |
| `frontend-dev` | Vue 3 + Vitest | `agents/frontend-dev.md` |
| `code-reviewer` | Quality review | `agents/code-reviewer.md` |
| `e2e-tester` | Playwright E2E | `agents/e2e-tester.md` |
| `integration-dev` | Dev-окружение | `agents/integration-dev.md` |
| `tester` | Тесты | `agents/tester.md` |

## Rules

| Rule | Описание |
|------|----------|
| `security.md` | Security checklist (auth, injection, PII) |
| `git.md` | Git workflow (branch → PR → merge) |

## Skills

| Skill | Описание |
|-------|----------|
| `add-feature` | Полный цикл добавления фичи |
| `review` | Code review |
| `security-check` | Security audit |

## Settings

`settings.json` — permissions + hooks:
- Deny: `rm -rf`, `git push --force`, `git reset --hard`, `DROP`
- Hook: `ruff check --fix` после каждого Edit/Write

## Отличия от `.claude/`

| | `.claude/` (оригинал) | `.kimi/` (адаптация) |
|---|----------------------|---------------------|
| Backend path | `backend/` | `server/` |
| Frontend | React + TypeScript | Vue 3 + JavaScript |
| Package manager | `uv` | `venv` |
| CI/CD | GitHub Actions + Helm | Пока не настроено |

## Workflow

1. **Анализ** — читаем код, понимаем архитектуру
2. **Backend** — model → schema → service → route → tests
3. **Frontend** — component → API integration → tests
4. **Review** — security + quality checklist
5. **Tests** — pytest + vitest + playwright
6. **Commit** — только после явного разрешения пользователя
