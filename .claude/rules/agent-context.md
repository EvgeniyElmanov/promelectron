---
description: Project-wide agent memory system. Read at the start of EVERY session before doing anything else.
paths:
  - ".agent/**"
  - "README.md"
  - "ARCHITECTURE.md"
  - "AUDIT.md"
---

# Agent Bootstrap

At the start of EVERY session, you MUST:

1. Read `.agent/START_HERE.md` — understand your role and onboarding
2. Read `.agent/CONTEXT.md` — current project status and focus
3. Read `.agent/BACKLOG.md` — what needs to be done (current sprint)
4. Read `.agent/BLOCKERS.md` — what is blocked right now
5. Read `.agent/AGENTS.md` — your zone, permissions, and prohibitions

Only THEN start working on user requests.

If `.agent/` files are missing or corrupted, report it immediately to the user.

## Quick context

- **Project:** Promelectron — marketplace (Ozon-style)
- **Stack:** FastAPI + Vue 3 + PostgreSQL + Redis + K8s
- **Test env:** https://promelectron-test.aidrivencode.ru
- **Current phase:** Sprint 1 preparation (payments + guest cart)
- **Tests:** Backend 102/102 ✅, Frontend 77/77 ✅, E2E 95/95 ✅

## Rules

- Update `.agent/CONTEXT.md` before ending your session
- Never commit secrets — env vars only through K8s Secrets
- Never modify `.github/` or `.infra/helm/` without explicit permission
- Agent-first: all code changes go through specialized agents
