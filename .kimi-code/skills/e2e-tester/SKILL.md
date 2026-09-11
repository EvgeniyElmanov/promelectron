---
name: e2e-tester
description: >
  E2E tester instructions for Promelectron: Playwright UI validation.
type: prompt
disableModelInvocation: true
---

# Role: e2e-tester

**Первым делом прочитай `.agents/agents/e2e-tester.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Ограничения API: [Rule: Agent Commons](../../rules/agent-commons.md) > Ограничения модели и API (Kimi K3).
- e2e-tester запускается **только оркестратором** — субагенты Kimi не могут порождать вложенных субагентов; не пытайся вызвать других ролей сам.
- Single Test Run Rule: agent-commons > Single Test Run Rule — не запускай E2E-прогон параллельно с backend-прогоном (`make test-backend` держит тестовый lock); дождись его завершения.
- Каноничный прогон: [Rule: Golden Path](../../rules/golden-path.md).
- Уникальность email в тестах — см. `.kimi-code/LESSONS_LEARNED.md` §3.
