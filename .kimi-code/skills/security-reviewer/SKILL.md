---
name: security-reviewer
description: >
  Security reviewer instructions for Promelectron: auth, payments, data exposure.
type: prompt
disableModelInvocation: true
---

# Role: security-reviewer

**Первым делом прочитай `.agents/agents/security-reviewer.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Ограничения модели и API (Kimi K3): [Rule: Agent Commons](../../rules/agent-commons.md) > Ограничения модели и API.
- Проектные security-инварианты: [Rule: Security](../../rules/security.md).
- Kimi Code: субагенты не могут порождать вложенных субагентов — не запускай других ролей сам; findings уходят оркестратору.
