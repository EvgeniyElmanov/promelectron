---
name: review
description: >
  Code review skill for Promelectron e-commerce project.
  Performs security audit, quality checks, and test coverage analysis on current changes
  or specified files. Writes findings to .agent/REVIEW_FINDINGS.md.
  Can run in full mode (security + quality + tests), security-only mode, or quick mode.
  Triggers on: review, code review, проверь код, findings, quality, audit, ревью,
  проверка, security review, code quality.
argument-hint: "[--security-only] [--quick] [<files>]"
---

# /review — Code Review

Проведи code review текущих изменений. Не редактируй код — только пиши findings.

---

## Modes

| Режим | Флаг | Что проверяет |
|-------|------|---------------|
| Full | (default) | Security + Quality + Tests |
| Security-only | `--security-only` | Только security checks |
| Quick | `--quick` | Только критические issues |

---

## Step 1: Get Diff

```bash
git diff
```

Или если указаны файлы:
```bash
git diff -- <files>
```

---

## Step 2: Security Checks (skip if not --quick)

### Authentication
- [ ] Все новые endpoints имеют auth guards
- [ ] Admin endpoints проверяют admin роль
- [ ] Пользователи могут получать только свои данные

### Injection
- [ ] Нет raw SQL с string formatting
- [ ] Все inputs валидируются через Pydantic
- [ ] Нет command injection

### Data Exposure
- [ ] Нет PII в логах
- [ ] Нет паролей/tokens в API responses
- [ ] Нет debug endpoints

### Business Logic
- [ ] Цены из БД, не от клиента
- [ ] Stock проверяется атомарно (`SELECT FOR UPDATE`)
- [ ] Количества в корзине валидированы (positive)
- [ ] Order totals считаются на сервере

### Path Traversal
- [ ] Filename санитизирован (`os.path.basename` + `os.path.realpath` check)

---

## Step 3: Quality Checks

### Backend
- [ ] Бизнес-логика в `services/`, не в route handlers
- [ ] Type hints на публичных методах
- [ ] Обработка ошибок (не голые 500)
- [ ] N+1 queries? (`selectinload` где нужно)
- [ ] Async/await для DB-операций

### Frontend
- [ ] Composition API (`<script setup>`)
- [ ] `data-testid` для E2E-селекторов
- [ ] Обработка loading/error/empty states
- [ ] Нет `console.log` / `debugger`

### General
- [ ] Код следует существующим конвенциям проекта
- [ ] Нет хардкода секретов или URL
- [ ] Комментарии объясняют "почему", не "что"

---

## Step 4: Tests Check

- [ ] Тесты на новый код присутствуют
- [ ] Тесты покрывают happy path и error cases
- [ ] Существующие тесты не сломаны
- [ ] E2E селекторы (`data-testid`) добавлены при изменении UI

---

## Step 5: Write Findings

Запиши в `.agent/REVIEW_FINDINGS.md` (или `.agent/<task-id>/review/findings.md`):

```markdown
# Code Review: <task-id или дата>
- **Status:** APPROVED | FIXES_NEEDED
- **Scope:** <files reviewed>
- **Reviewer:** code-reviewer

## Security
- [x] No issues
- [ ] **[S001] MEDIUM | <тип>**
  - **File:** `path:line`
  - **Problem:** <описание>
  - **Fix:** <как исправить>

## Quality
- [x] No issues
- [ ] **[Q001] LOW | <тип>**
  - **File:** `path:line`
  - **Problem:** <описание>
  - **Fix:** <как исправить>

## Tests
- [x] Tests present and adequate
- [ ] **[T001] HIGH | Missing tests**
  - **Module:** <что не покрыто>
  - **Expected:** <какие тесты нужны>

## Human Decisions (если есть)
- [ ] **[H001]** <вопрос, требующий решения пользователя>
```

---

## Step 6: Report

Сообщи пользователю:
```
📋 Code Review завершён

**Status:** APPROVED / FIXES_NEEDED
**Security:** <X issues>
**Quality:** <X issues>
**Tests:** <X issues>

**Критичные:**
- <список>

**Файл:** `.agent/REVIEW_FINDINGS.md`
```

---

## Rules

- **НЕ редактируй** исходный код — только findings
- **НЕ отмечай** findings как VERIFIED — это делает разработчик после фикса
- Классифицируй по критичности: CRITICAL | HIGH | MEDIUM | LOW
- Security issues = HIGH или CRITICAL по умолчанию
- При APPROVED — кратко, что понравилось (не просто "ок")
