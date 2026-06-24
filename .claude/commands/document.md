# /document

This command is implemented as the **`document` skill** — the single source of truth lives in
[`.claude/skills/document/SKILL.md`](../skills/document/SKILL.md).

Follow that skill: derive a slug, prepare a scratchpad workspace, fan out read-only
`general-purpose` research sub-agents (Codebase / Database / Web / GitHub — only the axes that
matter) in **one** message, then a single synthesis pass writes the concise Markdown doc. Everything
lives under the scratchpad dir — nothing is committed, no PR. Report in Russian and offer to copy
into `docs/` only if asked.

Arguments: `<что задокументировать; можно с #issue / PR-ссылками и явным scope>`
