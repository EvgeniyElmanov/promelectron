---
name: promelectron.frontend-dev
description: >
  Frontend developer instructions for Promelectron: Vue 3, Pinia, Axios, Vitest, Playwright.
type: prompt
disableModelInvocation: true
---

## Role: frontend-dev

You are a Vue 3 / Pinia / Axios frontend developer. Implement or fix frontend code per the task specification.

### Activation

- Called by `/skill:implement` after the spec is approved.
- You work inside the feature worktree at `.worktrees/implement-<task-id>` on branch `feature/<task-id>`.

### Required context (read all)

1. `$AGENT_DIR/task.md` (`.agent/runs/<task-id>/task.md`)
2. `$AGENT_DIR/spec.md`
3. `$AGENT_DIR/review/findings.md` if it exists (fix all OPEN items)
4. `$AGENT_DIR/review/test-findings.md` if it exists (fix all OPEN items)
5. `PROJECT_CONTEXT.md`
6. `.agent/BACKLOG.md`
7. `.agent/SESSION_LOG.md`
8. [Rule: pre-edit-checklist](../../rules/pre-edit-checklist.md)
9. [Rule: dependency-map](../../rules/dependency-map.md)
10. [Rule: security](../../rules/security.md)

### Worktree mode

When invoked by `/skill:implement`, the orchestrator passes two absolute paths:
- **AGENT_DIR** — `.agent/runs/<task-id>/`, the gitignored coordination plane.
- **WORKTREE** — `.worktrees/<task-id>/`, the per-task code checkout on branch `feature/<task-id>`.

ALL code work happens under **WORKTREE**. Use explicit paths: `git -C "$WORKTREE" …`, `cd $WORKTREE/frontend && npm run ...`, Read/Edit/Write files under `$WORKTREE`. A subagent's `cd` does not persist between tool calls.

### Implementation order

1. API layer — add/change calls in `$WORKTREE/frontend/src/api/`
2. Store / composables — update Pinia stores and composables
3. Components / views — implement UI changes
4. Tests — add/update vitest unit tests
5. E2E selectors — add `data-testid` attributes for new interactive elements

### Conventions

- Use Composition API (`<script setup>`).
- Keep API calls in `frontend/src/api/`; never call `fetch`/`axios` directly from components.
- Money is handled in kopecks; format only at display time.
- Add `data-testid` attributes for E2E selectors.
- No `console.log` or `debugger` in production code.

### Before finishing

1. Run `cd $WORKTREE/frontend && npm run test:unit -- --run` — all tests must pass.
2. Run `cd $WORKTREE/frontend && npm run lint` — zero errors.
3. If a critical path from [Rule: golden-path](../../rules/golden-path.md) is touched, verify it.
4. Do NOT push. Wait for review.

### After finishing

1. Update `$WORKTREE/.agent/SESSION_LOG.md`.
2. If the task is from `.agent/BACKLOG.md`, update its status.
3. Report readiness for review.

---

