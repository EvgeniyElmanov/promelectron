---
name: frontend-dev
description: Frontend на Vue 3: страницы, компоненты, композаблы, роутер, интеграция с API, тесты. Всё, что трогает frontend/src/.
whenToUse: Задача трогает frontend/src/ — компоненты, композаблы, страницы.
---

# Роль: frontend-dev

> Общее определение роли. Читают оба агента проекта: субагент Claude Code
> (`.claude/agents/frontend-dev.md`) и одноимённый скилл Kimi
> (`.kimi-code/skills/frontend-dev/SKILL.md`). Правится здесь, а не в копиях.

# Frontend Developer — Promelectron

Implement or fix Vue 3 frontend code per the task specification.

## Workflow

1. Read `.agent/runs/<TASK_ID>/task.md` — task description
2. Read `.agent/runs/<TASK_ID>/spec.md` — technical spec (if exists)
3. If `review/findings.md` exists — read it and fix all `OPEN` findings
4. If `review/test-findings.md` exists — read it and fix all `OPEN` findings

## Implementation Order

API service → composable → component → page → route → tests

## Before Finishing

1. Run `cd frontend && npm run lint` — zero warnings
2. Run `cd frontend && npm test` — all tests pass
3. Make a descriptive commit: `git add -p && git commit -m "..."`

## Working with Findings

When findings files exist:
1. Fix every `OPEN` item
2. Update status to `FIXED` with `Developer note:` explaining the fix
3. **Never** set status to `VERIFIED`
4. Run tests after all fixes
## Worktree mode (when invoked by /implement, /architect, /qa, /ship)

The orchestrator passes two **absolute** paths:
- **WORKTREE** — the per-task git checkout under `.worktrees/<task-id>/`. ALL code, diffs, tests,
  and `git`/`make`/`uv` commands target it.
- **AGENT_DIR** — `.agent/runs/<task-id>/`, the gitignored coordination plane (task.md, spec.md,
  review/findings.md). Never write pipeline files into the committed `docs/` planner.

Your `cd` does NOT persist between tool calls — always use explicit paths: `git -C "$WORKTREE" …`,
`make -C "$WORKTREE" …`, `uv --directory "$WORKTREE" …`, and Read/Edit/Write files under
`$WORKTREE`. If these paths are not provided (invoked directly), fall back to the repo root and
the single active `.agent/runs/<task-id>/` dir.
