# /sessions

This command is implemented as the **`sessions` skill** — the single source of truth lives in
[`.claude/skills/sessions/SKILL.md`](../skills/sessions/SKILL.md); lock rules are shared with the
Kimi twin via [`ai-launcher/CONVENTIONS.md`](../../ai-launcher/CONVENTIONS.md).

Compute the current wave from live state (open issues, branches, PRs, free locks) and emit it as
numbered terminals with ready-to-paste `make ai PROMPT=…` commands — plus an explicit list of what
NOT to launch and why (shared locks, waiting on the owner).

Arguments: none
