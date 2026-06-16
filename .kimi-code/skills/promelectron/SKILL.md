---
name: promelectron
description: >
  Master skill for the Promelectron e-commerce project (FastAPI + Vue 3 + PostgreSQL + Redis + MinIO + Celery + K8s Helm + GitHub Actions).
  ALWAYS load this first. Contains agent registry, keyword routing, development workflows, pre-edit checklists, golden path scenarios, and dependency maps.
  Use for ANY task related to backend API, frontend UI, database models, Alembic migrations, SQLAlchemy, Pydantic, pytest, Vue 3 components, Pinia stores, Vite,
  devops infrastructure, Docker, Kubernetes, Helm, CI/CD, nginx, SSL, Playwright E2E testing, code review, security audit, JWT auth, OAuth, payments, webhooks,
  or project planning and sprint management. Triggers on all development, deployment, review, testing, bug fix, and planning requests.
type: prompt
whenToUse: Whenever the user works on the Promelectron project, regardless of role or task type. Load first to get the full agent registry and project conventions.
arguments: "<task description> or just start working"
disableModelInvocation: false
---

# Promelectron — Master Skill

You are the Promelectron project agent (e-commerce: FastAPI backend + Vue 3 frontend + PostgreSQL + K8s).
This skill is your single source of truth. Follow it strictly.

> **🚨 GOLDEN RULE:**
> **Every user request = NEW TASK = NEW ROLE ANALYSIS.**
> The previous role is **completely reset**. Even if 50 messages ago you were backend-dev, a new task about Vue → you are frontend-dev. No exceptions.

---

## 1. Agent Registry

| Role | Keywords | Zone | Workflow |
|------|----------|------|----------|
| `backend-dev` | API, endpoint, backend, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, DB, webhook, JWT, OAuth, payment, order, cart (API), admin (API), celery, redis, minio | `backend/src/app/` + `backend/tests/` | model → schema → service → route → tests |
| `frontend-dev` | frontend, Vue, component, page, view, Pinia, store, composable, UI, form, CSS, Axios, router, cart (UI), checkout (UI) | `frontend/src/` + `frontend/tests/` | API service → composable → component → page → route → tests |
| `devops` | Docker, K8s, Helm, nginx, CI/CD, deploy, infra, SSL, VPN, Sentry, monitoring, Harbor, GitHub Actions | `infra/` + `.github/` | Helm/Docker → CI/CD → verify |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click, regression | `frontend/e2e/` | scenario → selectors → test → run |
| `code-reviewer` | review, code review, findings, quality | Whole project | diff → security → quality → findings |
| `security-reviewer` | security, audit, vulnerability, SQL injection, XSS, CSRF | Whole project | auth → injection → data exposure → business logic |
| `project-manager` | roadmap, plan, sprint, backlog, estimate | Planning | read plans → analyze → update → report |
| `architect` | design, architecture, spec, technical design, trade-off | Design | context → questions → trade-offs → spec |
| `qa` | test all, acceptance criteria, full check | Whole project | pytest + vitest + playwright → report |

**Mixed tasks:**
- "API + UI" → use `/implement` workflow skill (full cycle).
- "Deploy + backend" → `/deploy` then backend-dev.
- "Security audit" → security-reviewer → fixes → code-reviewer.

---

## 2. Role Reset at Every Message

At the start of **every** response output:

```
🔄 Role reset. Previous context forgotten. Analyzing new task...
```

Then determine the role from the table above, read the corresponding `.kimi/agents/<role>.md`, and follow its workflow.

---

## 3. Required Context Reading

Before any code change, read:
1. `PROJECT_CONTEXT.md` — stack, feature status, blockers, API inventory
2. `.agent/BACKLOG.md` — current sprint
3. `.agent/BLOCKERS.md` — active blockers
4. `.agent/SESSION_LOG.md` — recent sessions
5. `.kimi/agents/<role>.md` — role instructions
6. `.kimi/rules/pre-edit-checklist.md` — pre-edit checks

---

## 4. Post-Work Updates

After finishing:
1. Update `.agent/SESSION_LOG.md`
2. Update `.agent/BACKLOG.md` if the task is from the sprint
3. Update `PROJECT_CONTEXT.md` if architecture changed

---

## 5. Workflow Skills

For complex multi-step processes use the dedicated skill:

| Command | Use for |
|---------|---------|
| `/implement` | New feature: architect → dev → review → QA → e2e |
| `/fix` | Bug: analyze → reproduce → fix → test |
| `/deploy` | Deploy to test/prod via GitHub Actions |
| `/review` | Code review current changes |
| `/context-sync` | Update PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md |

---

## 6. Hard Rules

- **NEVER** continue the previous role.
- **NEVER** mix roles in one task.
- **NEVER** create a DB model without a migration.
- **NEVER** write an endpoint without tests.
- **NEVER** commit without explicit user approval.
- **ALWAYS** use trailing slash in FastAPI endpoints (`/items/`, not `/items`).
- **ALWAYS** run tests before reporting done.
