# /backlog-pick

This command is implemented as the **`backlog-pick` skill** — the single source of truth lives in
[`.claude/skills/backlog-pick/SKILL.md`](../skills/backlog-pick/SKILL.md).

Follow that skill exactly: fetch the GitHub Issue → create `.agent/runs/gh-<N>/` and write
`task.md` (GitHub-Issue format) → optionally move the Project card `start → In Progress` (ask
first) → hand off to `/brainstorm gh-<N>` or `/implement gh-<N>`. The issue stays open.

Arguments: `<issue#|#5|gh-5>`
