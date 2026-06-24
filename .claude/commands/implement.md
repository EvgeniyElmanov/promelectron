# /implement

This command is implemented as the **`implement` skill** — the single source of truth lives in
[`.claude/skills/implement/SKILL.md`](../skills/implement/SKILL.md).

Follow that skill's pipeline exactly: fetch task (GitHub Issue or free text) → isolate in a git
worktree → spec via the architect → parallel backend/frontend dev → parallel review → QA → PR,
moving the GitHub Project card `start → In Progress` and `PR opened → In Review` along the way
(the internal agent review/QA loops never move the card).

Arguments: `<issue#|gh-5|task text> [--quick] [--backend-only] [--frontend-only] [--serial] [--qa]`
