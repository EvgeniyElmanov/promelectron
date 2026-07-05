---
name: context-sync
description: >
  Synchronize and update Promelectron project context files.
  Analyzes git history, test status, codebase changes, and active blockers
  to update PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, and SESSION_LOG.md.
  Use when returning to the project after a break, when context files seem stale,
  before starting a new sprint, or for project health checks.
type: prompt
whenToUse: When the user asks to sync context, update context, check project status, or after a long pause.
arguments: "[--full] [--backlog-only] [--blockers-only] [--quick]"
disableModelInvocation: false
---

# /skill:context-sync — Синхронизация контекста проекта

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю, отчёты и обновления контекстных файлов пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Синхронизируй `PROJECT_CONTEXT.md`, `.agent/BACKLOG.md`, `.agent/BLOCKERS.md` с реальностью.

## Language / Язык

Следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule / Языковое правило. При русскоязычном пользователе пиши reports и обновления контекста на русском.

---

## Поведение флагов

- `--full` — запустить все проверки, включая E2E и валидацию Helm.
- `--backlog-only` — обновить только `.agent/BACKLOG.md`.
- `--blockers-only` — обновить только `.agent/BLOCKERS.md`.
- `--quick` — пропустить долгие тесты и E2E; использовать только git status + recent log.

---

## Step 1: Чтение текущего состояния

Прочитай параллельно:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. `.agent/PLANNING_HANDOFF.md`

Запиши `last_update` из frontmatter PROJECT_CONTEXT.md.

---

## Step 2: Проверка размера контекста активных задач (Kimi K2.7-Code)

Для каждой активной директории задачи в `.agent/runs/<task-id>/` следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check.

```bash
for d in .agent/runs/*/; do
  task_id="$(basename "$d")"
  python scripts/implement-pipeline.py check-context "$task_id"
done
```

---

## Step 3: Анализ истории Git

```bash
git log --since="<last_update>" --oneline --no-merges
git log --oneline -30
```

Ищи:
- Новые фичи (`feat:`)
- Исправления (`fix:`)
- Рефакторинги (`refactor:`)
- Инфра-изменения (`infra:`, `deploy:`)
- Новые миграции

---

## Step 4: Проверка статуса тестов

По умолчанию (если не `--quick`):

```bash
make test-backend 2>&1 | tail -20
make test-frontend 2>&1 | tail -20
```

Если `--full`:

```bash
make pre-push 2>&1 | tail -40
```

Если тесты не могут запуститься (например, нет Docker), зафиксируй блокер.

---

## Step 5: Сканирование блокеров

Для каждого блокера в `BLOCKERS.md`:
- `grep` по коду — возможно, уже исправлен?
- Проверь дедлайны > 2 дней → отметь как escalated
- Проверь владельца и статус

---

## Step 6: Поиск новых блокеров

Запусти быстрые health checks (пропусти при `--quick`):

```bash
# Alembic: проверка консистентности модели и БД (read-only)
cd backend && alembic check 2>&1 || echo "Alembic drift detected"

# Lint
make lint-backend 2>&1 | tail -10
```

Новые блокеры:
- `alembic check` сообщает о drift
- Тесты падают на main
- CI workflow сломан
- Отсутствует env var в `.env.example`

---

## Step 7: Обновление PROJECT_CONTEXT.md

Обнови frontmatter:

```yaml
---
sprint: "<current>"
sprint_dates: "<dates>"
last_update: "<today>"
last_commit: "<hash>"
commit_message: "<message>"
blockers_count: <N>
blockers_p0: <N>
blockers_p1: <N>
backend_tests: "<X/Y>"
frontend_tests: "<X/Y>"
e2e_tests: "<X/Y or N/A>"
---
```

Обнови разделы:
- What works now
- What is in progress
- Active blockers

Добавь краткий changelog внизу.

---

## Step 8: Обновление BACKLOG.md

Для каждой задачи спринта:
- Код существует? `grep` / `find`
- Тесты есть? `find`
- Роуты зарегистрированы? проверь `backend/src/app/main.py`
- Frontend связан? проверь views/router/API calls
- Env vars заданы? проверь `config.py`, `.env.example`
- CI/CD покрывает? проверь `.github/workflows/`

Отмечай done только с доказательством (commit или файл). Добавляй `(commit: abc1234)` при отметке done.

---

## Step 9: Обновление BLOCKERS.md

- Перенеси разрешённые блокеры в "Resolved"
- Обнови дедлайны
- Отметь escalated (>2 дней)
- Добавь новые блокеры из Step 6

---

## Step 10: Обновление SESSION_LOG.md

Добавь сводку по сессии context sync:
- Дата
- Ключевые изменения с last_update
- Результаты тестов
- Новые/разрешённые/escalated блокеры

---

## Step 11: Отчёт

Сообщи пользователю на русском:
- Что было обновлено
- Ключевые изменения с last_update
- Результаты тестов
- Новые/разрешённые/escalated блокеры
- Готовность спринта

---

## Rules / Правила

- Evidence first — only facts from code and git.
- Do not delete completed tasks — move to "Completed".
- Date every status change.
- Preserve history — append-only changelog.
- If BACKLOG.md conflicts with code, code wins.
- Do not move the GitHub Project board.

---
