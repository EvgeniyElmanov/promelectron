# Agent-First Rule (адаптировано под Kimi CLI)

> Используй специализированные агенты как **памятку и чеклист**, но помни: в Kimi CLI ты работаешь напрямую.

## Как работают агенты в Kimi CLI

В Kimi CLI нет «sub-processов». Агенты — это **промпты-инструкции** в `.kimi/agents/*.md`.  
Ты читаешь инструкцию агента и сам выполняешь задачу, следуя его правилам.

## Когда читать инструкцию агента

**Обязательно прочитай** `agents/<role>.md` перед задачей, если:

1. **Задача >3 файлов** — refactoring, фича, баг
2. **Есть специализированный агент** для домена:
   - `backend-dev` — FastAPI, SQLAlchemy, миграции
   - `frontend-dev` — Vue 3, компоненты, API интеграция
   - `devops` — Helm, Docker, CI/CD
   - `code-reviewer` — качество кода
   - `security-reviewer` — security audit
   - `project-manager` — планирование, BACKLOG.md
3. **Меняешь `.agent/PLANNING_HANDOFF.md` или `.agent/BACKLOG.md`** — прочитай `project-manager.md`
4. **Делаешь security audit** — прочитай `security-reviewer.md`

## Когда можно НЕ читать

- Опечатка в одном слове
- Прочитать один известный файл для контекста
- Simple Q&A без изменений кода

## Anti-Patterns

- ❌ Начинать задачу без чтения `PROJECT_CONTEXT.md` и `BACKLOG.md`
- ❌ Писать backend-код без проверки `pre-edit-checklist.md`
- ❌ Менять модель БД без миграции
- ❌ Делать фичу backend + frontend в одной задаче (разбивай)

## Workflow

1. **Прочитай `SESSION_START.md`** — получи контекст
2. **Определи роль** — по задаче (или роутер определит)
3. **Прочитай `agents/<role>.md`** — правила зоны
4. **Прочитай `pre-edit-checklist.md`** — перед правкой кода
5. **Работай** — ты сам пишешь код, агент — это инструкция
6. **Прочитай `golden-path.md`** — перед финишем проверь критичные сценарии
7. **Отчёт** — обнови `SESSION_LOG.md`
