# Promelectron — Agent Memory System

Before every response, read and follow:
1. `.agent/START_HERE.md` — your onboarding
2. `.agent/CONTEXT.md` — current project status
3. `.agent/BACKLOG.md` — priorities and sprint tasks
4. `.agent/BLOCKERS.md` — active blockers
5. `.agent/AGENTS.md` — your role and prohibitions

## Project context

- **Name:** Promelectron — marketplace (Ozon/Wildberries style)
- **Stack:** FastAPI (Python 3.12) + Vue 3 + PostgreSQL 16 + Redis 7 + K8s Helm
- **Test env:** https://promelectron-test.aidrivencode.ru
- **Current focus:** Sprint 1 — real payments (ЮKassa) + guest cart
- **Tests:** Backend 102/102 ✅, Frontend 77/77 ✅, E2E 95/95 ✅

## Rules for all agents

- Update `.agent/CONTEXT.md` before ending session
- Never commit secrets — use env vars and K8s Secrets only
- Never modify `.github/` or `.infra/helm/` without explicit permission
- Agent-first: all code changes go through specialized agents (backend-dev, frontend-dev, devops)
- One-line fixes only (typos, obvious bugs) — everything else goes through agents
- Do NOT rewrite from scratch without project-manager approval
- Do NOT break CI/CD — check pipeline is green before considering work done

## Emergency

- Secret leaked in code → immediately notify user + rotate secret
- CI/CD down → devops agent, notify user
- Production incident → devops + backend-dev, escalate to user
