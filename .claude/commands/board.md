# /board

This command is implemented as the **`board` skill** — the single source of truth lives in
[`.claude/skills/board/SKILL.md`](../skills/board/SKILL.md), and the format/lock/refresh rules
it follows live in [`ai-launcher/CONVENTIONS.md`](../../ai-launcher/CONVENTIONS.md) (shared with
the Kimi twin `/skill:board`).

Show the launch board `ai-launcher/BOARD.md` — what can be taken right now (🟢 with a free lock),
what waits on the owner, what is in flight, and which "⏰ waiting on a condition" tails can now be
checked. With `refresh`, reconcile the board against live state (open issues, branches, PRs,
locks) and rewrite it.

Arguments: `[refresh]`
