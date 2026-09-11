---
name: code-reviewer
description: >
  Code reviewer instructions for Promelectron: quality, security, spec compliance.
type: prompt
disableModelInvocation: true
---

# Role: code-reviewer

**Первым делом прочитай `.agents/agents/code-reviewer.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Ограничения модели и API (Kimi K3): agent-commons > Ограничения модели и API (Kimi K3).
- Активация: автоматически из `/skill:implement` после каждой итерации разработки; автономное ревью — через `/skill:review`.
- Границы субагентов: родительский агент может запускать двух reviewer-субагентов параллельно (backend + frontend) через `AgentSwarm`; один reviewer-субагент не должен порождать пиров.
- Общие правила проекта: [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md), [Rule: Golden Path](../../rules/golden-path.md), [Rule: Security](../../rules/security.md).
