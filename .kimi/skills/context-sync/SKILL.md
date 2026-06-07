---
name: context-sync
description: >
  Synchronize and update Promelectron project context files.
  Analyzes git history, test status, codebase changes, and active blockers
  to update PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, and SESSION_LOG.md.
  Use when returning to project after a break, when context files seem stale,
  before starting a new sprint, or for project health checks.
  Triggers on: sync, context, update context, status, project status,
  what's new, синхронизируй, статус, контекст, health check, sprint prep.
argument-hint: "[--full] [--backlog-only] [--blockers-only] [--quick]"
---

# /context-sync — Update Project Context

Актуализируй PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md на основе реального состояния кода.

---

## Step 1: Read Current State

Прочитай текущие файлы:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. `.agent/PLANNING_HANDOFF.md` (если есть)

Зафиксируй `last_update` из PROJECT_CONTEXT.md frontmatter.

---

## Step 2: Analyze Git History

```bash
git log --since="<last_update>" --oneline --no-merges
git log --oneline -30  # если last_update старый
```

Что искать:
- Новые фичи (feat:)
- Исправления (fix:)
- Рефакторинг (refactor:)
- Изменения в инфраструктуре (infra:, deploy:)
- Новые миграции

---

## Step 3: Check Test Status

### Backend
```bash
cd backend && pytest --tb=no -q 2>/dev/null || echo "Tests failed or not runnable"
```

### Frontend
```bash
cd frontend && npm test -- --run 2>/dev/null || echo "Tests failed or not runnable"
```

### E2E (если доступно)
```bash
cd frontend && npx playwright test --reporter=line 2>/dev/null || echo "E2E not runnable"
```

---

## Step 4: Scan for Stale Blockers

Для каждого блокера в BLOCKERS.md проверь:
- **BLK-xxx (backend):** grep по коду — может, уже исправлен?
- **BLK-xxx (devops):** проверь конфиги — может, уже настроено?
- **Дедлайн > 2 дней назад:** отметь как эскалированный

---

## Step 5: Check for New Blockers

Просканируй код на потенциальные проблемы:

```bash
# Проверь, что все миграции валидны
cd backend && alembic current 2>/dev/null || echo "Alembic issue"

# Проверь, что нет сломанных импортов
cd backend && python -c "from src.app.main import app" 2>/dev/null || echo "Import error"

# Проверь env vars (сравни .env.example с config.py)
grep -o 'Config\.[A-Z_]*' backend/src/app/core/config.py | sort -u
```

**Новые блокеры — это:**
- Миграция не применяется
- Тесты падают на main
- Настроен CI, но workflow сломан
- Отсутствует env var в `.env.example`, но используется в коде

---

## Step 6: Update PROJECT_CONTEXT.md

Обнови frontmatter:
```yaml
---
sprint: "<текущий спринт>"
sprint_dates: "<даты>"
last_update: "<сегодня>"
last_commit: "<hash>"
commit_message: "<message>"
blockers_count: <N>
blockers_p0: <N>
blockers_p1: <N>
backend_tests: "<X/Y>"
frontend_tests: "<X/Y>"
e2e_tests: "<X/Y>"
---
```

Обнови разделы:
- **"Что работает прямо сейчас"** — добавь новые готовые фичи
- **"Что в работе / не работает"** — обнови статусы
- **"Активные блокеры"** — обнови список

Добавь вниз краткую сводку изменений:
```markdown
---

## Changelog (auto-generated <YYYY-MM-DD>)

### Добавлено
- <новые фичи из git log>

### Исправлено
- <багфиксы из git log>

### Изменено
- <рефакторинг и infra>

### Блокеры (обновлено)
- <статус блокеров>
```

---

## Step 7: Update BACKLOG.md

Для каждой задачи в спринте проверь:
- **Code exists?** — grep по названию функции/компонента
- **Tests exist?** — `find tests -name "*<feature>*"`
- **Routes registered?** — проверь `main.py` или router includes
- **Frontend linked?** — проверь views, router, API calls
- **Env vars set?** — проверь `config.py`, `.env.example`

Правила обновления:
- Только отмечай `[x]` если есть доказательство (коммит или файл)
- При отметке done добавь `(commit: abc1234)`
- Объясняй `[!]` — точный блокер
- Добавь `(updated: YYYY-MM-DD)` к изменениям статуса

---

## Step 8: Update BLOCKERS.md

- Удали/перемести в "Resolved" блокеры, которые исправлены
- Обнови дедлайны если нужно
- Отметь эскалированные (>2 дней)
- Добавь новые блокеры, найденные на Step 5

---

## Step 9: Report

Сообщи пользователю:
```
🔄 Context Sync завершён

**Обновлено:**
- PROJECT_CONTEXT.md: frontmatter + changelog
- BACKLOG.md: <X> задач проверено, <Y> обновлено
- BLOCKERS.md: <X> resolved, <Y> new, <Z> escalated

**Ключевые изменения с <last_update>:**
- <список коммитов>

**Тесты:**
- Backend: <X/Y>
- Frontend: <X/Y>
- E2E: <X/Y>

**Новые блокеры:**
- <список или "нет">

**Готовность к новому спринту:** <да/нет, причины>
```

---

## Rules

- **Evidence first** — только факты из кода и git, не предположения
- **Не удаляй** выполненные задачи — перемещай в "Completed"
- **Date everything** — все изменения статуса с датой
- **Preserve history** — append-only changelog
- При конфликте между BACKLOG.md и кодом — **код прав**, BACKLOG устарел
