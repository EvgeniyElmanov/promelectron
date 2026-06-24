# /ship

This command is implemented as the **`ship` skill** — the single source of truth lives in
[`.claude/skills/ship/SKILL.md`](../skills/ship/SKILL.md).

Follow that skill exactly: derive the task-id (and GitHub Issue, if any) from the current branch →
ensure everything is pushed → build the PR body from the task's spec → open the PR with
`gh pr create --base main` (with `Closes #<N>` for issue tasks) → move the GitHub Project card
`pr_opened → In Review`. It is the standalone version of `/implement` Step 7. Russian PR body, no
AI attribution; `/ship` never merges.

Arguments: `[issue#|gh-5|branch]` (optional — defaults to the current branch)
