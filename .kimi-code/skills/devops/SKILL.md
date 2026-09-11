---
name: devops
description: >
  DevOps instructions for Promelectron: Helm, Docker, CI/CD, secrets.
type: prompt
disableModelInvocation: true
---

# Role: devops

**Первым делом прочитай `.agents/agents/devops.md` — там определение роли, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило (преамбула для субагентов — раздел Full subagent prompt block там же). Кратко: при русскоязычном пользователе финальные ответы, отчёты и артефакты — на русском; код, команды, идентификаторы, пути и технические термины — в оригинале.
- Ограничения API (Kimi K3): [Rule: Agent Commons](../../rules/agent-commons.md) > Ограничения модели и API (Kimi K3).
- Обязательные правила: [Rule: Security](../../rules/security.md), [Rule: Pre-edit Checklist](../../rules/pre-edit-checklist.md).
- Kimi Code: субагенты не могут порождать вложенных субагентов — вся работа этой роли выполняется в текущем контексте.
