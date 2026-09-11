---
name: backend-dev
description: >
  Backend developer instructions for Promelectron: FastAPI, SQLAlchemy, Alembic, pytest.
type: prompt
disableModelInvocation: true
---

# Role: backend-dev

**Первым делом прочитай `.agents/agents/backend-dev.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Single Test Run Rule: agent-commons > Single Test Run Rule (`make test-backend` только foreground, дождись результата до отчёта; никаких фоновых прогонов после отчёта).
- Обязательный контекст Kimi-сессии (дополнение к task.md/spec.md из общего файла): `PROJECT_CONTEXT.md`, `docs/backlog.md`, `docs/journal/session-log.md` (tail ~200 строк), [Rule: Agent Commons](../../rules/agent-commons.md), [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md), [Rule: Dependency Map](../../rules/dependency-map.md), [Rule: Security](../../rules/security.md), [Rule: Golden Path](../../rules/golden-path.md).
- Ограничения API (Kimi K3): [Rule: Agent Commons](../../rules/agent-commons.md) > Ограничения модели и API (Kimi K3).
