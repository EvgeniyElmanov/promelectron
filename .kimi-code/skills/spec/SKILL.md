---
name: spec
description: >
  Standalone technical specification skill for Promelectron.
  Use when the user wants just the spec without running the full /skill:implement pipeline —
  to discuss an approach, share it with teammates, or do research-heavy planning before committing to a build.
  Fetches/creates the task in .agent/runs/<task-id>/, invokes the architect agent to write spec.md,
  drives the clarifications loop with the user, copies the plan to spec.md, and presents the result.
  Planning only — runs no development, creates no worktree, opens no PR.
type: prompt
whenToUse: When the user asks for a spec, technical design, architecture decision, or wants to plan a feature before implementation.
arguments: "<task description | issue#>"
disableModelInvocation: false
---

# /skill:spec — Автономная техническая спецификация

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю и артефакты (task.md, spec.md, reports, SESSION_LOG) пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Подготовь техническую спецификацию через агента **`architect`**. Пишет `.agent/runs/<task-id>/spec.md`.

Используй эту команду, когда нужна **только спецификация** без полного пайплайна `/skill:implement` — чтобы обсудить подход, поделиться с командой или провести research-heavy планирование перед разработкой.

## Language / Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило. При русскоязычном пользователе пиши `task.md`, `spec.md` и reports на русском.

---

## Step 0: Предварительные проверки

Проверь доступ к GitHub CLI, если входные данные могут ссылаться на GitHub Issue:

```bash
gh auth status
```

Если не работает — остановись и попроси пользователя выполнить `gh auth login`.

---

## Step 1: Подготовка

Запиши корень репозитория:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

Сгенерируй `<task-id>`: короткий slug в kebab-case из описания.

Создай координационную плоскость:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/research"
```

Установи `AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>`.

Напиши `$AGENT_DIR/task.md` по шаблону из [Rule: Task Template](../../rules/task-template.md), если он ещё не существует.

Если входные данные — ссылка на GitHub Issue (`#5`, `gh-5`, `5`):
- Получи его через `gh issue view`.
- Заполни `task.md` из тела issue.
- Запиши `github_issue: #N` в `task.md`.

---

## Step 1.5: MCP — подтягивание Jira / Confluence (опционально)

Если в `task.md` указаны `jira_issue` или `confluence_spec_url`, используй MCP-сервер `atlassian` для получения дополнительного контекста и допиши его в `task.md` (раздел `External context`).

```text
Инструменты MCP:
- atlassian/jira_get_issue — для jira_issue
- atlassian/confluence_get_page / confluence_search_pages — для confluence_spec_url
```

Что извлечь:
- Jira: `summary`, `description`, `labels`, `components`, acceptance criteria (если есть в description или custom fields).
- Confluence: `title`, `body.storage` (plain text/html), связанные страницы.

Не дублируй уже имеющееся описание — только дополнительные детали и AC. Если MCP-сервер недоступен (нет токенов), продолжай без него и отметь это в `task.md`.

---

## Step 2: Проверка размера контекста (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Context Size Check перед запуском субагентов.

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

Если `ESTIMATED_TOKENS` >= 150000, читай `$AGENT_DIR/CONTEXT_SUMMARY.md` вместо полной истории.

---

## Step 3: Research fan-out (опционально)

Для нетривиальных задач запусти read-only research субагентов параллельно через инструмент `AgentSwarm` с `subagent_type: explore`. Каждый пишет `$AGENT_DIR/research/<axis>.md`.

Оси: `libraries`, `best-practices`, `codebase-integration`, `external-api-docs`.

items: `["libraries", "best-practices", "codebase-integration", "external-api-docs"]`

Архитектор синтезирует research-файлы в `$AGENT_DIR/research.md`.

---

## Step 4: Запуск архитектора

Запусти субагента architect через инструмент `Agent` с `subagent_type: plan`.

```text
Предварь этот промпт комбинированной преамбулой из Rule: Agent Commons (раздел Full subagent prompt block).

Ты — архитектор Promelectron.

Прочитай (параллельно, где возможно):
1. $AGENT_DIR/task.md
2. $AGENT_DIR/research/*.md (если есть) и синтезируй в $AGENT_DIR/research.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/architect/SKILL.md`
8. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
9. [Rule: Planning](../../rules/planning.md)
10. [Rule: Agent Commons](../../rules/agent-commons.md)

Ты уже запущен как `plan`-субагент — контекст plan уже отключает shell и включает планирование, поэтому НЕ вызывай EnterPlanMode повторно. Пиши спецификацию прямо в plan-файл, предоставленный контекстом plan-субагента, затем вызови ExitPlanMode.

Затем:
1. Исследуй кодовую базу в $PROJECT_ROOT, чтобы понять точки интеграции.
2. Предложи 2–3 альтернативных подхода, если они имеют смысл.
3. Напиши техническую спецификацию в plan-файл. Включи: Task Type, Analysis, Decisions (D-01, D-02, ...), Components Affected, Parallelization Plan, Technical Design, API Changes, Must-haves, Acceptance Criteria, Out of Scope, Risks.
4. Если требование неоднозначно и влияет на дизайн, установи Status: NEEDS_CLARIFICATION и перечисли открытые вопросы.
5. Иначе установи Status: READY.
6. Вызови ExitPlanMode.

Do NOT write implementation code, tests, migrations, or config files.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 5: Копирование плана в координационную плоскость

После того как архитектор вызовет `ExitPlanMode`, скопируй содержимое plan-файла в `$AGENT_DIR/spec.md`.

Если пользователь отклонил или попросил доработки — отправь архитектора на доработку.

---

## Step 6: Цикл уточнений

Прочитай `$AGENT_DIR/spec.md`.

- **Если `Status: NEEDS_CLARIFICATION`:** покажи открытые вопросы пользователю через `AskUserQuestion`, допиши ответы в `## Clarifications` в `$AGENT_DIR/task.md`, затем перезапусти архитектора для обновления плана и скопируй его в `spec.md`.
- **Если `Status: READY`:** покажи краткое резюме — выбранный подход, API Contract, Must-haves, D-numbers.

Спроси пользователя: **"Спецификация готова. Начать реализацию через `/skill:implement <task-id>`?"**

---

## Step 7: Post-work updates

Обнови `$PROJECT_ROOT/.agent/SESSION_LOG.md` сводкой по сессии спецификации.

Если задача из спринта, обнови `.agent/BACKLOG.md` статусом `ready` или `in_progress`.

---

## Rules / Правила

- Только планирование — никакого worktree, кода или PR.
- Никогда не пиши временные файлы в закоммиченную планировочную директорию `.agent/`.
- Спецификация принадлежит архитектору; ты только управляешь циклом.
- Всегда копируй plan-файл в `$AGENT_DIR/spec.md` перед циклом уточнений.

---
