# /backlog-done

This command is implemented as the **`backlog-done` skill** — the single source of truth lives in
[`.claude/skills/backlog-done/SKILL.md`](../skills/backlog-done/SKILL.md).

Follow that skill exactly: close the GitHub Issue with `gh issue close` — `--reason completed`
(default) or `--reason "not planned"` (when `drop`) → optionally post a closing comment if the user
gave a reason → move the Project card to `Done` when completed. Closing is a status flip; nothing is
deleted.

Arguments: `<issue#|#5|gh-5> [drop] [reason…]`
