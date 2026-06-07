---
name: implement
description: >
  Full development cycle skill for Promelectron e-commerce project.
  Use for implementing new features, adding pages, creating API endpoints, building Vue components,
  adding database models, schemas, services, migrations, or any task requiring code changes.
  Runs optional architect phase, creates git branch, develops backend and/or frontend,
  performs code review loop (max 3 iterations), QA loop (max 2 iterations), and creates merge request.
  Triggers on: implement, feature, add, create, build, develop, new page, new API, endpoint,
  component, model, schema, migration, page, view, фича, добавь, сделай, создай, страница,
  компонент, endpoint, API, модель, схема, миграция, сервис.
argument-hint: "<task description> [--quick] [--backend-only] [--frontend-only]"
---

# /implement — Full Development Cycle

Реализуй новую фичу от идеи до Merge Request.

---

## Step 1: Parse and Setup

Извлеки из запроса пользователя:
- Описание задачи (всё до флагов)
- Флаги: `--quick`, `--backend-only`, `--frontend-only`

Сгенерируй `<task-id>` — короткий kebab-case slug.
Примеры: `add-product-filters`, `fix-cart-stock-check`, `yookassa-integration`

Создай рабочую директорию:
```bash
mkdir -p .agent/<task-id>/review
```

Запиши `.agent/<task-id>/task.md`:
```markdown
# Task: <task-id>
## Description
<полное описание задачи>
## Flags
<активные флаги или "none">
## Date
<YYYY-MM-DD>
```

---

## Step 2: Architect Phase (skip if --quick)

Ты — архитектор. Проанализируй задачу в контексте проекта:

1. Прочитай существующий код, чтобы понять структуру
2. Задай уточняющие вопросы пользователю, если что-то неясно — **жди ответа**
3. Предложи подход с trade-offs, если есть варианты — **жди выбора пользователя**
4. Напиши `.agent/<task-id>/spec.md`:

```markdown
# Technical Specification: <task-id>

## Task Type
Feature | Bug Fix | Refactoring

## Analysis
[Как задача вписывается в существующую архитектуру]

## Decisions
- **D-01:** [Решение с обоснованием — разработчик должен следовать строго]

## Components Affected
- Backend: [файлы/модули] | Не затронут
- Frontend: [файлы/модули] | Не затронут
- Infra: [файлы/модули] | Не затронут

## Technical Design
[Что создать/изменить и как]

## Must-haves
- [ ] Поведение 1
- [ ] Поведение 2

## Acceptance Criteria
- [ ] Критерий 1
- [ ] Критерий 2

## Out of Scope
- [Что задача НЕ включает]
```

Сообщи пользователю: **"Spec готов. Начинаю реализацию?"**
**Жди подтверждения перед продолжением.**

---

## Step 3: Git Branch

```bash
git fetch origin
git checkout -b feature/<task-id> origin/main
```

---

## Step 4: Implementation

На основе Components Affected в spec.md вызови соответствующих агентов через `Agent` tool.

### Если затронут backend (и не `--frontend-only`):
Вызови `backend-dev`:
```
Ты — backend-dev проекта Promelectron.
Прочитай:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .kimi/agents/backend-dev.md
7. .kimi/rules/pre-edit-checklist.md

Реализуй backend-часть задачи строго по workflow:
model → schema → service → route handler → tests

После работы:
1. Запусти pytest -x и ruff check
2. Обнови .agent/SESSION_LOG.md
3. Сообщи результат: что сделано, файлы, статус
```

### Если затронут frontend (и не `--backend-only`):
Вызови `frontend-dev`:
```
Ты — frontend-dev проекта Promelectron.
Прочитай:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .kimi/agents/frontend-dev.md
7. .kimi/rules/pre-edit-checklist.md

Реализуй frontend-часть задачи строго по workflow:
API service → composable → component → page → route → tests

После работы:
1. Запусти npm run lint && npm test -- --run
2. Обнови .agent/SESSION_LOG.md
3. Сообщи результат: что сделано, файлы, статус
```

**Порядок:** backend → frontend (если оба).

---

## Step 5: Code Review Loop (max 3 iterations)

### Каждая итерация:

1. Вызови `code-reviewer`:
```
Проведи code review изменений для задачи <task-id>.
Прочитай .agent/<task-id>/spec.md.
Проверь:
- Security (auth guards, SQL injection, PII exposure)
- Quality (бизнес-логика в services, type hints, обработка ошибок)
- Тесты (наличие тестов на новый код)

Результат запиши в .agent/<task-id>/review/findings.md в формате:
- Status: APPROVED | FIXES_NEEDED
- Security: [x] или [ ] Issue: описание
- Quality: [x] или [ ] Issue: описание
- Tests: [x] или [ ] Missing tests for: ...
```

2. Прочитай `.agent/<task-id>/review/findings.md`

3. **Если APPROVED** → иди в Step 6

4. **Если FIXES_NEEDED:**
   - Покажи пользователю summary findings + любые `[H-xxx]` Human Decision items
   - Для H-items: жди решения пользователя, обнови spec.md
   - Вызови разработчика(ов) для исправления:
```
Исправь findings из .agent/<task-id>/review/findings.md.
Task directory: .agent/<task-id>/
Исправь все OPEN items и отметь их FIXED с примечанием разработчика.
```
   - Повтори с начала итерации

5. **После 3-й итерации, всё ещё FIXES_NEEDED:**
   Покажи пользователю оставшиеся open findings. Спроси, как продолжить. Не продолжай автоматически.

---

## Step 6: QA Loop (max 2 iterations)

1. Вызови `qa` (или выполни сам, если нет qa-агента):
```
Запусти тесты и проверь acceptance criteria.
Task directory: .agent/<task-id>/
Прочитай spec.md. Результат запиши в .agent/<task-id>/review/test-findings.md.
```

2. Прочитай `.agent/<task-id>/review/test-findings.md`

3. **Если TESTS_PASSED** → иди в Step 7

4. **Если TESTS_FAILED:**
   - Покажи пользователю summary failures
   - Вызови разработчика(ов):
```
Исправь ошибки тестов из .agent/<task-id>/review/test-findings.md.
Task directory: .agent/<task-id>/
```
   - Вернися в **Step 5** (code review) — код изменился, нужен re-review

5. **После 2 QA-итераций, всё ещё TESTS_FAILED:**
   Покажи полный test-findings.md и спроси пользователя, как продолжить.

---

## Step 7: Create Merge Request

1. Push ветку:
```bash
git push -u origin feature/<task-id>
```

2. Создай PR через `gh pr create`:
```bash
gh pr create \
  --title "feat: <краткое описание>" \
  --base main \
  --head feature/<task-id> \
  --body "$(cat <<'EOF'
## Summary
<что сделано>

## Changes
<изменённые файлы/компоненты>

## Test Results
- Backend: pytest X/Y passed
- Frontend: vitest X/Y passed

## Acceptance Criteria
<checked list from spec.md>
EOF
)"
```

3. Сообщи пользователю:
   - Ссылка на PR
   - Изменённые файлы
   - Результаты тестов
   - Незакрытые H-items (если есть)
   - "После merge PR → test deploy автоматически через GitHub Actions"
   - "Для prod → запусти workflow вручную с environment=prod"

---

## Rules

- **НИКОГДА** не пушь напрямую в `main` — только через MR
- `.agent/` добавлен в `.gitignore` — файлы остаются локально
- Разработчик НЕ отмечает findings как VERIFIED — только ревьюер
- Ревьюер НЕ редактирует исходный код — только пишет findings.md
- QA НЕ редактирует исходный код — только пишет test-findings.md
- Максимум 3 code-review + 2 QA итерации, затем эскалация пользователю
- После каждого этапа обновляй `.agent/SESSION_LOG.md`
