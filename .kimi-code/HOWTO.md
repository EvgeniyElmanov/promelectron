# 📘 HOWTO — работа с агентами Promelectron в Kimi Code CLI

> Практическое руководство: как маршрутизировать задачи, поддерживать чистый контекст и выбирать правильный workflow.

## Языковое примечание

Когда пользователь общается на русском языке, основной агент и все субагенты должны рассуждать и думать на русском. Родительский агент должен явно сообщать субагентам, что исходный пользователь общается на русском, чтобы они тоже рассуждали на русском.

## 1. Какую проблему мы решили

Kimi Code CLI обнаруживает проектные навыки из `.kimi-code/skills/`. Мы вынесли все workflow-навыки туда, чтобы `/skill:implement`, `/skill:fix`, `/skill:review` и `/skill:deploy` работали из коробки.

## 2. Три способа работы

### Способ A: workflow-навыки (рекомендуется)

Используй для полных циклов разработки фич, исправления багов, ревью и деплоев.

```
/skill:implement "Add promo codes to cart"
/skill:fix "Race condition in cart add"
/skill:review
/skill:deploy test
```

Skill сам порождает субагентов и управляет pipeline.

### Способ B: фиксированная роль

Используй, если работаешь в одной роли весь день.

```
Role: backend-dev. Task: add email validation to registration.

Read PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, SESSION_LOG.md.
Load `/skill:backend-dev` or read `.kimi-code/skills/backend-dev/SKILL.md` and [Rule: Pre-edit Checklist](./rules/pre-edit-checklist.md).
After work update SESSION_LOG.md.
```

### Способ C: dispatcher (ad-hoc задачи)

Используй, когда не знаешь роль и не нужен полный workflow.

```
Load `/skill:dispatcher` or read `.kimi-code/skills/dispatcher/SKILL.md` and follow its instructions strictly.
Task: Create an API for promo codes.
```

## 3. Как работает `/skill:implement`

1. Создаёт `.agent/runs/<task-id>/` (gitignored coordination plane)
2. Создаёт git worktree `.worktrees/<task-id>` на ветке `feature/<task-id>`
3. Порождает субагента architect в plan mode → пишет `spec.md` → ждёт одобрения
4. Порождает субагента(ов) developer в worktree
5. Порождает субагента code reviewer → пишет `review/findings.md` (максимум 3 итерации)
6. Порождает субагента QA/e2e-tester → пишет `review/test-findings.md`
7. Открывает GitHub PR через `gh pr create` и публикует открытые пункты `[H-xxx]` как комментарии PR
8. Отчитывается пользователю; merge только с явным одобрением

## 4. Bash-хелперы

```bash
make check            # lint + test
make dev              # запустить стек
make stop             # остановить стек
make test-backend     # backend tests (PostgreSQL in Docker)
make test-frontend    # frontend unit tests
make test-e2e         # Playwright E2E tests
make status           # git + services
```

Pipeline helper:

```bash
python scripts/implement-pipeline.py setup "Add promo codes to cart"
python scripts/implement-pipeline.py create-worktree <task-id>
python scripts/implement-pipeline.py cleanup <task-id>
```

## 5. Как понять, что роль переключилась

При использовании dispatcher или workflow-навыка субагент должен заявлять свою роль в начале. Если агент отвечает в неправильном стиле, перезагрузи skill или начни новую сессию.

## 6. Роли и зоны

| Роль | Зона |
|------|------|
| `backend-dev` | `backend/src/app/`, `backend/tests/` |
| `frontend-dev` | `frontend/src/` |
| `devops` | `infra/`, `.github/workflows/` |
| `e2e-tester` | `frontend/e2e/` |
| `code-reviewer` | diff → findings |
| `security-reviewer` | security findings |
| `project-manager` | планы, бэклог, роадмап |
| `qa` | полная пирамида тестирования |
| `integration-dev` | локальное dev-окружение |

## 7. Обязательные файлы

Агенты читают:
- `PROJECT_CONTEXT.md`
- `.agent/BACKLOG.md`
- `.agent/BLOCKERS.md`
- `.agent/SESSION_LOG.md`
- `.kimi-code/skills/<role>/SKILL.md` — инструкции роли (flat Kimi skill)
- [Rule: Pre-edit Checklist](./rules/pre-edit-checklist.md)

Агенты обновляют:
- `.agent/SESSION_LOG.md`
- `.agent/BACKLOG.md`
- `.agent/BLOCKERS.md`
- `PROJECT_CONTEXT.md` (если изменилась архитектура)

## 8. Решение проблем

### Skill не распознаётся
- Проверь, что `.kimi-code/skills/` существует и содержит файлы `SKILL.md`.
- Kimi Code CLI загружает навыки автоматически из `.kimi-code/skills/`.

### Агент не переключает роль
1. Перезагрузи workflow skill: `/skill:implement ...`
2. Начни новую сессию Kimi CLI
3. Явно укажи роль: `Role: frontend-dev. Task: ...`

### `make task` / `make ask` удалены
Старые хелперы `make task`, `make ask`, `make auto` и `make task-compact` удалены. Вместо них используй workflow-навыки:
```
/skill:implement "Add promo codes to cart"
/skill:fix "Race condition in cart add"
/skill:promelectron
```

### Агент не обновил SESSION_LOG.md
В workflow-навыках это часть промпта субагента. В режиме фиксированной роли добавь явно:
```
After work update SESSION_LOG.md.
```

## 9. Формат задачи (5 элементов)

```
[ROLE] Task: [one sentence]
File: [specific file or zone]
Related: [related files that will also change]
Do not break: [boundaries]
Verify: [how to confirm it works]
```

Подробнее см. [Rule: Prompt Format](./rules/prompt-format.md).

## 10. Чеклист быстрого старта

- [ ] Открыть Kimi CLI в корне проекта
- [ ] Запустить `/skill:implement "<описание фичи>"`
- [ ] Одобрить спецификацию architect
- [ ] Дать pipeline отработать
- [ ] После завершения проверить `.agent/SESSION_LOG.md`

## 11. Где почитать ещё

- [SESSION_START.md](../SESSION_START.md) — шаблоны входа в сессию
- [AGENTS.md](../AGENTS.md) — индекс агентов и high-level workflow
- [.kimi-code/AGENTS.md](./AGENTS.md) — активный индекс проектных инвариантов (загружается автоматически)
- [.kimi-code/skills/promelectron/SKILL.md](./skills/promelectron/SKILL.md) — мастер-skill / индекс ролей
- [ROUTER.md](../ROUTER.md) — документация по маршрутизации
- [Rule: Pre-edit Checklist](./rules/pre-edit-checklist.md) — проверки перед редактированием кода
