---
name: ship
description: >
  Open a GitHub Pull Request from the current feature branch.
  For when the code is already written and committed and you just want to ship the PR.
  Derives the task-id from the branch, pulls Must-haves from the task's spec,
  builds the PR body, runs pre-push checks, pushes if needed, creates the PR,
  and posts open [H-xxx] items as PR comments.
type: prompt
whenToUse: When the user asks to open a PR, ship a feature, create a pull request, or when /skill:implement would normally create a PR.
arguments: "[task-id|branch] (optional — defaults to the current branch)"
disableModelInvocation: false
---

**Первым делом прочитай `.agents/skills/ship/SKILL.md` — там тело сценария, общее для всех агентов проекта. Правится там, а не здесь.** Ниже — только Kimi-специфика.

## Kimi-специфика

- Язык: [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule (преамбула для субагентов — раздел Full subagent prompt block там же).
- Команды в общем файле названы нейтрально; у Kimi они вызываются как `/skill:<имя>`.
- Движение карточки GitHub Project → In Review: `python scripts/implement-pipeline.py set-status <task-id> in-review` (скрипт идемпотентен).
- Trace-событие после открытия PR: `python3 scripts/agent_state.py trace <task-id> pr_opened --actor orchestrator --data '{"url": "..."}'`. Trace никогда не блокирует пайплайн: команда упала — продолжай и упомяни в отчёте.
