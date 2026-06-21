---
description: Project-wide agent memory system. Read at the start of EVERY session before doing anything else.
paths:
  - ".agent/**"
  - "README.md"
  - "ARCHITECTURE.md"
  - "AUDIT.md"
  - "AGENTS.md"
  - "PROJECT_CONTEXT.md"
  - "SESSION_START.md"
---

# Agent Bootstrap

At the start of EVERY session, you MUST:

1. Read `AGENTS.md` — agent index, skills, rules, and permissions
2. Read `PROJECT_CONTEXT.md` — current project status and focus
3. Read `SESSION_START.md` — how to use the agent system
4. Read `.agent/BACKLOG.md` — what needs to be done (current sprint)
5. Read `.agent/BLOCKERS.md` — what is blocked right now

Only THEN start working on user requests.

If `.agent/` files are missing or corrupted, report it immediately to the user.

## Quick context

- **Project:** Promelectron — marketplace (Ozon-style)
- **Stack:** FastAPI + Vue 3 + PostgreSQL + Redis + K8s
- **Test env:** https://promelectron-test.aidrivencode.ru
- **Agent system:** Kimi Code CLI skills in `.kimi-code/skills/` and project-level instructions in `.kimi-code/AGENTS.md`

## Rules

- Update `PROJECT_CONTEXT.md` and `.agent/SESSION_LOG.md` before ending your session
- Never commit secrets — env vars only through K8s Secrets
- Never modify `.github/` or `.infra/helm/` without explicit permission
- Agent-first: all code changes go through specialized agents
