---
name: qa
type: prompt
description: >
  QA engineer role for Promelectron. Orchestrates the full test pyramid — backend pytest,
  frontend vitest, and Playwright E2E — and verifies Acceptance Criteria from spec.md.
  Activated automatically by /skill:implement after code review passes.
disableModelInvocation: true
---

# Role: qa

**Первым делом прочитай `.agents/agents/qa.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Kimi Code: субагенты не могут порождать вложенных субагентов — НЕ запускай e2e-tester сам; E2E-фазу запускает оркестратор отдельно (см. skill implement).
- Single Test Run Rule: agent-commons > Single Test Run Rule (`make test-backend` только foreground, никаких фоновых прогонов после отчёта).
