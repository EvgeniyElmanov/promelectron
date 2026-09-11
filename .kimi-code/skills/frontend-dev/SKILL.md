---
name: frontend-dev
description: >
  Frontend developer instructions for Promelectron: Vue 3, Axios, Vitest, Playwright.
type: prompt
disableModelInvocation: true
---

# Role: frontend-dev

**Первым делом прочитай `.agents/agents/frontend-dev.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Ограничения модели и API (Kimi K3): agent-commons > Ограничения модели и API — соблюдай лимиты контекста и retry policy.
- Обязательные правила перед кодом: [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md), [Rule: Dependency Map](../../rules/dependency-map.md), [Rule: Security](../../rules/security.md), [Rule: Golden Path](../../rules/golden-path.md) (проверка критического пути в «Before Finishing» общей роли).
- Kimi Code: субагенты не могут порождать вложенных субагентов — не делегируй; вся frontend-работа этой роли делается самим субагентом.
