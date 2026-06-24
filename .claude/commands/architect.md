# /architect

This command is implemented as the **`architect` skill** — the single source of truth lives in
[`.claude/skills/architect/SKILL.md`](../skills/architect/SKILL.md).

Follow that skill exactly: fetch the task (GitHub Issue or free text) into
`.agent/runs/<task-id>/` → invoke the `architect` agent to write `spec.md` → drive the
clarifications loop with the user → present the spec and ask (in Russian) if it's good. Planning
only: runs no development, opens no PR, and never moves the GitHub Project board. Hand off with
`/implement <task-id>` to build it.

Arguments: `<issue#|gh-5|free text>`
