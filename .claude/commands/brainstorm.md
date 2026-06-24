# /brainstorm

This command is implemented as the **`brainstorm` skill** — the single source of truth lives in
[`.claude/skills/brainstorm/SKILL.md`](../skills/brainstorm/SKILL.md).

Follow that skill exactly: interactive research/brainstorm — parallel research fan-out
(`general-purpose` sub-agents) → interactive synthesis with honest trade-offs → save a
study-friendly `.agent/runs/<task-id>/brainstorm.md`, then hand off to `/architect <task-id>` or
`/implement <task-id>`. Pure exploration: no spec, no code, never moves the GitHub Project board.

Arguments: `<тема / вопрос для изучения | issue#|gh-5>`
