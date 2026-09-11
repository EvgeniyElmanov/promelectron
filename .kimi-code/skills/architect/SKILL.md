---
name: architect
description: >
  Architect instructions for Promelectron: design, spec, trade-offs.
type: prompt
disableModelInvocation: true
---

**Первым делом прочитай `.agents/agents/architect.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Planning mode у Kimi: роль запускается как `plan`-субагент — контекст уже отключает shell и фокусирует на планировании. НЕ вызывай `EnterPlanMode` повторно; спецификацию пиши напрямую в plan-файл, предоставленный контекстом plan-субагента, и в конце вызови `ExitPlanMode`.
