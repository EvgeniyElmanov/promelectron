# /backlog-list

This command is implemented as the **`backlog-list` skill** — the single source of truth lives in
[`.claude/skills/backlog-list/SKILL.md`](../skills/backlog-list/SKILL.md).

Show the **GitHub backlog**: open GitHub Issues on `AutonomaCo/promelectron` grouped by their
GitHub Project board status column (Todo / In Progress / In Review / Done). Read-only. Optional
filter by status or label. After listing, offers `/implement <issue#>` or `/backlog-pick <issue#>`.

Arguments: `[фильтр: Todo|In Progress|In Review|Done|<label>]`
