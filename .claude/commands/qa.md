# /qa

This command is implemented as the **`qa` skill** — the single source of truth lives in
[`.claude/skills/qa/SKILL.md`](../skills/qa/SKILL.md).

Follow that skill: locate the task's `.agent/runs/<task-id>/` and `.worktrees/<task-id>/`, invoke
the `qa` agent to run pytest + vitest (and Playwright E2E for UI/API changes), verify the spec's
Acceptance Criteria, write `review/test-findings.md`, and report pass/fail + F-/H-findings in
Russian. The standalone form of `/implement` Step 6; it never edits source and never moves the board.

Arguments: `<issue#|gh-5|task-id|slug> [--e2e]`
