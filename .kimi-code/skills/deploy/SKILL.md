---
name: deploy
description: >
  Deploy Promelectron to test or production Kubernetes environment.
  Triggers GitHub Actions workflow via gh CLI, watches deployment progress,
  runs E2E smoke tests, and reports status. Requires explicit user confirmation for production deployments.
type: flow
whenToUse: When the user explicitly asks to deploy, release, rollout, or deploy to test/production/staging. This skill is manual-only.
arguments: "<test|prod>"
---

**Первым делом прочитай `.agents/skills/deploy/SKILL.md` — там тело сценария, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Команды в общем файле названы нейтрально; у Kimi они вызываются как `/skill:<имя>`.
- Перед деплоем дополнительно читай обязательный контекст проекта: `PROJECT_CONTEXT.md`, `docs/backlog.md`, `docs/blockers.md`, `docs/journal/session-log.md`, [Rule: Security](../../rules/security.md).
- Trace-события: `python3 scripts/agent_state.py trace <task-id> deploy_smoke_failed --actor orchestrator` и `deploy_rollback` (при rollback). Trace никогда не блокирует пайплайн.
