---
name: promelectron
description: >
  Master skill for the Promelectron e-commerce project (FastAPI + Vue 3 + PostgreSQL + Redis + MinIO + Celery + K8s Helm + GitHub Actions).
  ALWAYS load this first. Contains agent registry, keyword routing, development workflows, pre-edit checklists, golden path scenarios, and dependency maps.
  Use for ANY task related to backend API, frontend UI, database models, Alembic migrations, SQLAlchemy, Pydantic, pytest, Vue 3 components, composables, Vite,
  devops infrastructure, Docker, Kubernetes, Helm, CI/CD, nginx, SSL, Playwright E2E testing, code review, security audit, JWT auth, OAuth, payments, webhooks,
  or project planning and sprint management. Triggers on all development, deployment, review, testing, bug fix, and planning requests.
type: prompt
whenToUse: Whenever the user works on the Promelectron project, regardless of role or task type. Load first to get the full agent registry and project conventions.
arguments: "<task description> or just start working"
disableModelInvocation: true
---

# Promelectron — Master Skill

Ты — агент проекта Promelectron (e-commerce: FastAPI backend + Vue 3 frontend + PostgreSQL + K8s).
Этот skill — единый источник истины. Следуй ему строго.

> **🚨 ЗОЛОТОЕ ПРАВИЛО:**
> **Каждый запрос пользователя = НОВАЯ ЗАДАЧА = НОВЫЙ АНАЛИЗ РОЛИ.**
> Предыдущая роль **полностью сбрасывается**. Даже если 50 сообщений назад ты был backend-dev, новая задача про Vue → ты frontend-dev. Без исключений.

## Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило.
Все требования к русскому языку и преамбулы для субагентов живут там.

Kimi K3 работает в **обязательном thinking mode** (отключить нельзя; глубина задаётся `reasoning_effort`); в multi-turn tool calls возвращай полное assistant message unchanged, включая `reasoning_content`.
Если внутреннее рассуждение иногда переключается на английский, **не считай это ошибкой** — единственное жёсткое требование: пользовательские ответы, отчёты и артефакты должны соответствовать языку пользователя.

---

## 1. Реестр агентов

| Роль | Ключевые слова | Зона | Workflow |
|------|----------------|------|----------|
| `backend-dev` | API, endpoint, backend, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, DB, webhook, JWT, OAuth, payment, order, cart (API), admin (API), celery, redis, minio | `backend/src/app/` + `backend/tests/` | model → schema → service → route → tests |
| `frontend-dev` | frontend, Vue, component, page, view, composable, UI, form, CSS, Axios, router, cart (UI), checkout (UI) | `frontend/src/` + `frontend/tests/` | API service → composable → component → page → route → tests |
| `devops` | Docker, K8s, Helm, nginx, CI/CD, deploy, infra, SSL, VPN, Sentry, monitoring, Harbor, GitHub Actions | `infra/` + `.github/` | Helm/Docker → CI/CD → verify |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click, regression | `frontend/e2e/` | scenario → selectors → test → run |
| `code-reviewer` | review, code review, findings, quality | Whole project | diff → security → quality → findings |
| `security-reviewer` | security, audit, vulnerability, SQL injection, XSS, CSRF | Whole project | auth → injection → data exposure → business logic |
| `project-manager` | roadmap, plan, sprint, backlog, estimate | Planning | read plans → analyze → update → report |
| `architect` | design, architecture, spec, technical design, trade-off | Design | context → questions → trade-offs → spec |
| `qa` | test all, acceptance criteria, full check | Whole project | pytest + vitest + playwright → report |
| `integration-dev` | dev environment, services won't start, ports, health check | Local env | start → diagnose → stop |

**Смешанные задачи:**
- "API + UI" → используй workflow skill `/skill:implement` (полный цикл).
- "Deploy + backend" → `/skill:devops`, затем backend-dev.
- "Security audit" → security-reviewer → fixes → code-reviewer.

---

## 2. Сброс роли при каждом сообщении

В начале **каждого** выходного ответа:

```
🔄 Role reset. Previous context forgotten. Analyzing new task...
```

Затем определи роль по таблице выше, вызови соответствующий Kimi skill (`/skill:<role>`) или прочитай `.kimi-code/skills/<role>/SKILL.md` и следуй его workflow.

| Роль | Skill | Файл |
|------|-------|------|
| `backend-dev` | `/skill:backend-dev` | `.kimi-code/skills/backend-dev/SKILL.md` |
| `frontend-dev` | `/skill:frontend-dev` | `.kimi-code/skills/frontend-dev/SKILL.md` |
| `devops` | `/skill:devops` | `.kimi-code/skills/devops/SKILL.md` |
| `e2e-tester` | `/skill:e2e-tester` | `.kimi-code/skills/e2e-tester/SKILL.md` |
| `code-reviewer` | `/skill:code-reviewer` | `.kimi-code/skills/code-reviewer/SKILL.md` |
| `security-reviewer` | `/skill:security-reviewer` | `.kimi-code/skills/security-reviewer/SKILL.md` |
| `qa` | `/skill:qa` | `.kimi-code/skills/qa/SKILL.md` |
| `project-manager` | `/skill:project-manager` | `.kimi-code/skills/project-manager/SKILL.md` |
| `integration-dev` | `/skill:integration-dev` | `.kimi-code/skills/integration-dev/SKILL.md` |
| `dispatcher` | `/skill:dispatcher` | `.kimi-code/skills/dispatcher/SKILL.md` |
| `architect` | `/skill:architect` | `.kimi-code/skills/architect/SKILL.md` |

Shared rules (reference markdown, не skills):
- Pre-edit checklist: [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md)
- Golden path: [Rule: Golden Path](../../rules/golden-path.md)
- Dependency map: [Rule: Dependency Map](../../rules/dependency-map.md)
- Security: [Rule: Security](../../rules/security.md)
- Prompt format: [Rule: Prompt Format](../../rules/prompt-format.md)
- Task template: [Rule: Task Template](../../rules/task-template.md)
- Planning: [Rule: Planning](../../rules/planning.md)
- Known pitfalls: [Rule: Known Pitfalls](../../rules/known-pitfalls.md)

`.kimi-code/AGENTS.md` — активный индекс инвариантов проекта (загружается автоматически). Роли живут в плоских скиллах `.kimi-code/skills/<role>/`.

---

## 3. Обязательное чтение контекста

Перед любым изменением кода прочитай:
1. `PROJECT_CONTEXT.md` — стек, статус фич, блокеры, инвентарь API
2. `.agent/BACKLOG.md` — текущий спринт
3. `.agent/BLOCKERS.md` — активные блокеры
4. `.agent/SESSION_LOG.md` — недавние сессии
5. Соответствующий `<role>` skill в `.kimi-code/skills/<role>/SKILL.md` — инструкции роли
6. [Rule: Agent Commons](../../rules/agent-commons.md) — язык, retry policy, обработка контекста
7. [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md) — проверки перед редактированием

---

## 4. Проверка размера контекста (Kimi K3)

Перед запуском субагентов оцени размер контекста задачи:

```bash
python scripts/implement-pipeline.py check-context <task-id>
```

- Если `ESTIMATED_TOKENS` >= 600000, читай `.agent/runs/<task-id>/CONTEXT_SUMMARY.md` вместо полной истории.
- Логируй оценочное количество токенов в `.agent/SESSION_LOG.md`.

Kimi K3 имеет контекстное окно 1M токенов с обязательным thinking mode. Порог 600K (~60% окна) оставляет место для `reasoning_content`, выводов инструментов и системных инструкций.

---

## 5. Политика повторных попыток (Retry Policy)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Политика повторных попыток (Retry Policy).

---

## 6. Обновления после работы

После завершения:
1. Обновить `.agent/SESSION_LOG.md`
2. Обновить `.agent/BACKLOG.md`, если задача из спринта
3. Обновить `PROJECT_CONTEXT.md`, если изменилась архитектура

---

## 7. Workflow-навыки

Для сложных многошаговых процессов используй dedicated skill:

| Команда | Для чего |
|---------|----------|
| `/skill:implement` | Новая фича: architect → dev → review → QA → e2e |
| `/skill:fix` | Баг: analyze → reproduce → fix → test |
| `/skill:review` | Code review текущих изменений |
| `/skill:qa-gate` | Перезапуск QA для существующей задачи |
| `/skill:context-sync` | Обновить PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md |
| `/skill:plan-maintainer` | Операции с бэклогом |
| `/skill:spec` | Автономная техническая спецификация |
| `/skill:ship` | Открыть PR для готовой feature-ветки |

---

## 8. Жёсткие правила

- **NEVER** продолжать предыдущую роль.
- **NEVER** смешивать роли в одной задаче.
- **NEVER** создавать DB model без миграции.
- **NEVER** писать endpoint без тестов.
- **NEVER** коммитить без явного одобрения пользователя.
- **ALWAYS** использовать trailing slash в FastAPI endpoints (`/items/`, not `/items`).
- **ALWAYS** запускать тесты перед отчётом о завершении.
- **ALWAYS** привязывать GitHub Issue перед началом разработки в `/skill:implement`.
- **ALWAYS** обновлять статус GitHub Project board на границах фаз: spec approved → In progress, PR open → In review, merged → Done.
- **NEVER** создавать дублирующие GitHub Issues для одного и того же `task-id`; переиспользуй существующий `github_issue` из `task.md`.
