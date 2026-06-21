# ROUTER — Agent routing for Promelectron

> Describe the task — the system picks the right agent, gathers context, and starts working.

## Language note

When the user communicates in Russian, the main agent and all subagents must reason and think in Russian. The parent agent must explicitly tell subagents that the original user communicates in Russian so they also reason in Russian. Final replies to the user must be in Russian, while code, commands, identifiers, file paths, and technical terms stay in their original form.

## Quick start

### Option 1: Workflow skills (recommended)

```
/skill:implement "Add promo codes to cart"     # full feature cycle
/skill:fix "Race condition in cart add"        # bug-fix workflow
/skill:deploy test                             # deploy via GitHub Actions
/skill:review                                  # code review current changes
/skill:context-sync                            # update project context files
```

### Option 2: Fixed role (when you know who you need)

```
Role: backend-dev. Task: add email validation to registration.
```

### Option 3: Dispatcher (ad-hoc tasks)

```
Load `/skill:dispatcher` or read `.kimi-code/skills/dispatcher/SKILL.md` and follow its instructions strictly.
Task: Create an API for promo codes.
```

## How routing works

| Role | Keywords in task | When to choose |
|------|------------------|----------------|
| `implement` | New feature, API, page, component | Full cycle: architect → dev → review → QA |
| `fix` | Bug, error, crash, not working | Analyze → reproduce → fix → test |
| `deploy` | Deploy, release, production | GitHub Actions → watch → E2E smoke test |
| `backend-dev` | API, endpoint, backend, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, DB, table, webhook, JWT, OAuth (backend), payment, order, cart (API), auth (backend), admin (API) | Backend-only tasks |
| `frontend-dev` | frontend, Vue, component, page, view, Pinia, store, composable, UI, UX, form, responsive, CSS, Axios, router, localStorage, cart (UI), login (UI), checkout (UI) | Frontend-only tasks |
| `devops` | Docker, K8s, Kubernetes, Helm, nginx, CI/CD, deploy, infra, SSL, VPN, backup, Sentry, monitoring, pod, container, GitHub Actions, workflow, secret, config | Infrastructure tasks |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click, end-to-end, regression, spec | E2E scenarios |
| `code-reviewer` | review, code review, findings, quality | Code review |
| `security-reviewer` | security, audit, vulnerability, SQL injection, XSS, CSRF | Security audit |
| `project-manager` | roadmap, plan, sprint, prioritize, backlog, estimate, planning | Planning |
| `qa` | test, acceptance criteria, full check, qa | Full test pyramid |
| `integration-dev` | dev environment, services won't start, ports, health check | Local environment ops |

**Mixed tasks** (e.g. "API and frontend for promos"):
1. `/skill:implement` picks the primary role and may run backend + frontend sequentially.
2. For ad-hoc mixed work, use the dispatcher.

## Architecture

```
User describes task
       │
       ▼
┌─────────────────────────────┐
│  /skill:implement or /skill:fix skill   │
│  (in .kimi-code/skills/)    │
└─────────────┬───────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  ┌─────────┐  ┌──────────┐
  │ Reads   │  │ Reads    │
  │PROJECT_ │  │BACKLOG,  │
  │CONTEXT  │  │BLOCKERS  │
  └────┬────┘  └────┬─────┘
       │            │
       └─────┬──────┘
             ▼
  ┌──────────────────────┐
  │ Spawns subagent      │
  │ (architect/dev/QA)   │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │ Writes task artifacts│
  │ (spec, findings)     │
  └──────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `.kimi-code/skills/promelectron/SKILL.md` | Master skill with agent registry and golden rules |
| `.kimi-code/skills/implement/SKILL.md` | Full feature cycle |
| `.kimi-code/skills/fix/SKILL.md` | Bug-fix workflow |
| `.kimi-code/skills/review/SKILL.md` | Code review workflow |
| `.kimi-code/skills/deploy/SKILL.md` | Deployment workflow |
| `.kimi-code/skills/context-sync/SKILL.md` | Context synchronization |
| `.kimi-code/skills/plan-maintainer/SKILL.md` | Backlog/planning maintenance |
| `.kimi-code/skills/<role>/SKILL.md` | Role instructions (flat Kimi skills) |
| `.kimi-code/rules/*.md` | Shared conventions (reference markdown) |
| `PROJECT_CONTEXT.md` | Single source of truth |
| `.agent/BACKLOG.md` | Current sprint |
| `.agent/BLOCKERS.md` | Active blockers |
| `.agent/SESSION_LOG.md` | Session log |

## Adding a new role

1. Create a new flat skill under `.kimi-code/skills/<role>/SKILL.md`
2. Add the role to `.kimi-code/skills/promelectron/SKILL.md` (master index)
3. Add keywords to `.kimi-code/skills/dispatcher/SKILL.md`
4. Update `ROUTER.md` and `SESSION_START.md`
5. If the role is part of `/skill:implement`, update `.kimi-code/skills/implement/SKILL.md`
