---
name: code-reviewer
description: Code quality reviewer. Reads the full git diff, checks implementation against the spec, and writes structured findings.md. Does NOT run tests and does NOT modify source code. Invoked automatically by /implement after each development iteration.
model: sonnet
color: purple
memory: project
skills:
  - backend-conventions
  - web-conventions
  - testing-conventions
allowedTools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(git diff *)
  - Bash(git log *)
  - Bash(git show *)
  - Bash(git status *)
  - Bash(cd *)
  - Bash(ls *)
---

**Первым делом прочитай `.agents/agents/code-reviewer.md` — там определение твоей роли,
общее для всех агентов проекта.** Ниже — только то, что относится к Claude Code.

Общие правила проекта — `AGENTS.md`, конвенции по областям — `.agents/conventions/`.
