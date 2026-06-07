---
name: fix
description: >
  Bug fix workflow for Promelectron e-commerce project.
  Use when user reports a bug, error, crash, exception, test failure, or broken functionality
  in backend, frontend, or infrastructure. Analyzes the bug, determines the correct role,
  reproduces with a minimal test, fixes the root cause (not symptoms), runs tests,
  checks golden path if affected, and reports results.
  Triggers on: fix, bug, broken, error, crash, exception, fail, failing, test failure,
  не работает, почини, исправь, баг, ошибка, упал, сломался, тест падает, regression.
argument-hint: "<bug description> [--backend] [--frontend] [--infra] [--e2e]"
---

# /fix — Bug Fix Workflow

Исправь баг системно: анализ → воспроизведение → фикс → тест → проверка.

---

## Step 1: Analyze and Route

### 1.1 Сброс роли
```
🔄 Сброс роли. Анализирую баг...
```

### 1.2 Определи роль по описанию бага

| Тип бага | Роль |
|----------|------|
| API возвращает ошибку, 500, 422, БД, миграция, race condition | `backend-dev` |
| UI не отображается, CSS сломан, router, форма, валидация на фронте | `frontend-dev` |
| Docker не стартует, Helm, CI/CD, деплой, secrets, nginx | `devops` |
| Playwright тест падает, селектор не найден, timeout | `e2e-tester` |
| Тест pytest/vitest падает после изменений | определи по зоне |

**Если не уверен:** спроси пользователя.

### 1.3 Заяви роль
```
🎯 Роль определена: <ROLE> (багфикс)
```

---

## Step 2: Read Context

Прочитай:
1. `PROJECT_CONTEXT.md` — стек, статус, блокеры
2. `.agent/BACKLOG.md` — есть ли уже задача на этот баг
3. `.agent/BLOCKERS.md` — не блокер ли это
4. `.agent/SESSION_LOG.md` — что недавно менялось (причина регрессии?)
5. `.kimi/agents/<ROLE>.md` — workflow роли
6. `.kimi/rules/pre-edit-checklist.md`
7. `.kimi/rules/golden-path.md` — если затронут критичный сценарий

---

## Step 3: Reproduce

### 3.1 Найди место
- Используй `git log --oneline -10` — что недавно менялось
- Используй `git diff` — есть ли незакоммиченные изменения
- Grep по ключевым словам ошибки

### 3.2 Воспроизведи
- **Backend:** напиши минимальный тест, который воспроизводит баг
- **Frontend:** опиши шаги воспроизведения или напиши unit-тест
- **E2E:** запусти конкретный тест: `npx playwright test <spec>`

**Правило:** Если не можешь воспроизвести — не чини. Спроси пользователя о деталях.

---

## Step 4: Fix Root Cause

### 4.1 Диагностика
Задай себе вопросы:
- Что изменилось недавно? (git log)
- Это регрессия или новый баг?
- Граничный случай (null, пустой список, деление на ноль)?
- Race condition?
- Неправильный тип данных?
- Отсутствует валидация?

### 4.2 Фикс
- Исправь **причину**, не **симптом**
- Не добавляй `try/except` вокруг всего подряд
- Если меняешь модель — создай миграцию
- Если меняешь API contract — обнови frontend layer

### 4.3 Проверь зависимости
По `dependency-map.md`: если правил файл X — проверь/обнови связанные Y.

---

## Step 5: Test

### 5.1 Тест на фикс
- Напиши/обнови тест, который проверяет исправление
- Тест должен был **падать до фикса** и **проходить после**

### 5.2 Регрессия
- Запусти тесты модуля: `pytest tests/test_<module>.py -x` или `npm test -- <pattern>`
- Запусти полный линт: `ruff check` / `npm run lint`

### 5.3 Golden Path (если затронут)
Если баг в: `auth`, `products`, `cart`, `orders`, `payments`, `checkout`:
- Проверь соответствующий golden path сценарий
- Не обязательно все, только затронутый модуль

---

## Step 6: Report

Обнови `.agent/SESSION_LOG.md`:
```markdown
## <YYYY-MM-DD> — Fix: <краткое описание бага>
- **Role:** <ROLE>
- **Root cause:** <причина>
- **Fix:** <что изменено>
- **Files:** `<file1>`, `<file2>`
- **Tests:** <добавлен/обновлён тест>
- **Golden path checked:** да/нет
- **Regression risk:** низкая/средняя/высокая
```

Обнови `.agent/BACKLOG.md` если баг был из спринта.

Сообщи пользователю:
```
✅ Баг исправлен.

**Причина:** <корневая причина>
**Фикс:** <что изменено>
**Файлы:** <список>
**Тесты:** <статус тестов>

Проверь, пожалуйста, что всё работает.
```

---

## Anti-Patterns (запрещено при фиксах)

- ❌ Не чини симптом вместо причины
- ❌ Не убирай тест, который падает — чини код
- ❌ Не добавляй `print`/`console.log` для дебага — используй debugger или нормальное логирование
- ❌ Не игнорируй flaky тест — разберись, почему он unstable
- ❌ Не делай `git commit` без разрешения пользователя
