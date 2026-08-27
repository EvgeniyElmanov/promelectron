---
name: qa-gate
description: >
  Standalone QA gate skill for Promelectron.
  Use to re-run the QA stage for a task that was already specced and built,
  without re-running the full /skill:implement pipeline.
  Locates the task's coordination plane (.agent/runs/<task-id>/) and worktree (.worktrees/<task-id>/),
  runs backend pytest + frontend vitest + Playwright E2E when UI/API changed,
  verifies Acceptance Criteria from spec.md, and writes review/test-findings.md.
type: prompt
whenToUse: When the user asks to QA a task, run tests for a task, verify a feature, or re-check after fixes.
arguments: "<task-id|slug> [--e2e]"
disableModelInvocation: false
---

# /skill:qa-gate — Автономный QA Gate

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю и артефакты (findings, reports, test-findings, SESSION_LOG) пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Запусти **QA gate** для одной задачи и запиши результаты в `.agent/runs/<task-id>/review/test-findings.md`.

Используй этот скилл, когда код уже написан и нужно перезапустить тесты / проверить acceptance criteria без полного пайплайна `/skill:implement`.

## Language / Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило. При русскоязычном пользователе пиши reports и findings на русском.

---

## Step 0: Валидация task-id

`task-id` должен соответствовать `^[a-z0-9-]+$`. Если содержит `..`, shell-метасимволы или пробелы — остановись и попроси пользователя ввести корректный task-id.

---

## Step 1: Локализация рабочего пространства

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"
```

- Если `$AGENT_DIR` отсутствует — остановись и скажи пользователю сначала запустить `/skill:spec <task-id>` или `/skill:implement <task-id>`.
- Если `$WORKTREE` отсутствует — остановись и скажи пользователю, что worktree удалён; пересоздай его через `/skill:implement <task-id>`.
- Если `$AGENT_DIR/spec.md` отсутствует — предупреди, что spec нет; QA-агент всё равно запускает тестовые suites.

Создай директорию review, если её нет:

```bash
mkdir -p "$AGENT_DIR/review"
```

---

## Step 2: Проверка размера контекста (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 600000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 3: Запуск qa-субагента

Запусти субагента `qa` через инструмент `Agent` с `subagent_type: coder`.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — QA-инженер для Promelectron.

Paths:
- AGENT_DIR = /abs/path/to/.agent/runs/<task-id>
- WORKTREE = /abs/path/to/.worktrees/<task-id>
- E2E flag: <yes|no>

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md (если есть)
3. $AGENT_DIR/review/findings.md (если есть)
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](../../rules/golden-path.md)
9. [Rule: Agent Commons](../../rules/agent-commons.md)

Затем:
1. Запусти backend-тесты в $WORKTREE: make -C "$WORKTREE" test-backend
2. Если задача меняла `backend/src/app/models/` или `backend/alembic/` — прогнать `make -C "$WORKTREE" migrate-check` (`alembic check`); exit != 0 → `TESTS_FAILED`.
3. Запусти frontend unit-тесты в $WORKTREE: make -C "$WORKTREE" test-frontend
4. Если фича затрагивает UI или пользовательские сценарии, или передан флаг --e2e — запусти E2E: `make -C "$WORKTREE" test-e2e`. Не делегируй E2E другому субагенту; при необходимости в запуске `e2e-tester` отдельно вернись к оркестратору после завершения.
5. Проверь каждый Acceptance Criterion из $AGENT_DIR/spec.md.
6. Запиши результаты в $AGENT_DIR/review/test-findings.md.
7. Обнови $PROJECT_ROOT/.agent/SESSION_LOG.md.

Do NOT edit source code.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 3.5: E2E-тестер (опционально, запускается оркестратором)

Если фича затрагивает UI/пользовательские сценарии или передан флаг `--e2e`, и результаты unit-тестов в порядке, запусти субагента `e2e-tester` **из основного агента** через инструмент `Agent` с `subagent_type: coder`. Не запускай e2e-tester изнутри qa-субагента.

Промпт аналогичен Step 7.5 `/skill:implement`. Передай:
- `$AGENT_DIR`
- `$WORKTREE`
- `feature scope` из spec.md
- Acceptance Criteria из spec.md

После завершения e2e-tester обновит `$AGENT_DIR/review/test-findings.md`.

---

## Step 4: Отчёт

Прочитай `$AGENT_DIR/review/test-findings.md` и отчитайся пользователю:
- Status: `TESTS_PASSED` or `TESTS_FAILED`
- Backend / frontend / E2E counts
- Open F-findings and H-findings
- Путь к report-файлу

Если `TESTS_FAILED`, предложи вызвать `/skill:implement <task-id>` или соответствующую роль разработчика для исправления, затем повторно `/skill:qa-gate <task-id>`.

---

## Правила

- QA-агент никогда не редактирует исходный код — только пишет findings.
- Do not move the GitHub Project board.
- Keep all reads/writes under `.agent/runs/<task-id>/` and `.worktrees/<task-id>/`.
- Always update `$PROJECT_ROOT/.agent/SESSION_LOG.md` after the QA gate.

---
