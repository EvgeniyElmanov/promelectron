# 🤖 AI Agent System — Promelectron

> Project-level instructions for Kimi Code CLI.  
> Loaded automatically from `.kimi-code/AGENTS.md` for every session in this project.

> **Note:** Role-specific instructions live in flat Kimi skills under `.kimi-code/skills/<role>/`.  
> Shared conventions live in `.kimi-code/rules/` (reference markdown, not skills).  
> This file is the master index and contains only project-wide invariants.

---

## Skill and rule registry

For the consolidated registry of role skills, workflow skills, and shared rules, see `.kimi-code/BUNDLE.md`.

---

## 🚨 GOLDEN RULE: REASON IN RUSSIAN / ЗОЛОТОЕ ПРАВИЛО: РАССУЖДАЙ НА РУССКОМ

When the user communicates in Russian, **ALL** your reasoning, thinking, internal monologue, analysis, planning, and self-correction **MUST** be in Russian.

Когда пользователь общается на русском языке, **ВСЁ** твоё рассуждение, мышление, внутренний монолог, анализ, планирование и самокоррекция **ДОЛЖНЫ** быть на русском.

- **NEVER switch to English** during reasoning. If you catch yourself thinking in English, immediately switch back to Russian.
- **НИКОГДА не переключайся на английский** во время рассуждения. Если заметил, что думаешь по-английски, немедленно вернись к русскому.
- Final replies to the user **MUST** be in Russian.
- When delegating to subagents, **explicitly tell them** that the original user communicates in Russian and they **MUST** reason in Russian.
- Keep code, commands, identifiers, file paths, and technical terms in their original form.
- Before producing a final reply, do a quick self-check: was all internal reasoning in this turn done in Russian? If not, redo it in Russian.

For the exact subagent preambles, see [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule.

## Subagent boundary

- Subagents launched via the `Agent` tool run in isolated context and **cannot schedule further nested subagents**.
- Only the main Agent (or a top-level skill invocation) may call `Agent` or `AgentSwarm`.
- For parallel work (e.g., review backend + frontend simultaneously), the **main agent** uses `AgentSwarm`; a single subagent must not try to spawn peers.

---

## Quick start

```bash
# Implement a new feature (full cycle)
/skill:implement "Add promo codes to cart"

# Write a spec without coding
/skill:spec "Add promo codes to cart"

# Fix a bug or failing tests
/skill:fix "Race condition in cart add"

# Review current changes
/skill:review

# Re-run QA for an existing task
/skill:qa-gate add-promo-codes-to-cart-0624

# Open a PR for the current branch
/skill:ship

# Deploy to test or prod
/skill:deploy test

# Sync project context
/skill:context-sync

# Maintain plans
/skill:plan-maintainer analyze
```

---

## Where things live

| Path | Purpose |
|------|---------|
| `.kimi-code/skills/` | Flat Kimi skills for roles and workflows |
| `.kimi-code/AGENTS.md` | This file — project-wide invariants only |
| `.kimi-code/rules/` | Shared conventions and reference docs |
| `.kimi-code/mcp.json` | MCP server configuration |
| `.kimi-code/config.example.toml` | Example user-level config |
| `scripts/implement-pipeline.py` | Helper for task IDs, git worktrees, review loops |
| `.agent/runs/<task-id>/` | Gitignored per-task coordination plane (`task.md`, `spec.md`, `review/findings.md`, `review/test-findings.md`) |
| `.worktrees/<task-id>/` | Isolated git worktree for the feature branch |

---

## Workflow overview

```
User: /implement "Add promo codes to cart"
        │
        ▼
   Create .agent/runs/<task-id>/
        │
        ▼
   git worktree add .worktrees/<task-id> -b feature/<task-id>
        │
        ▼
   Architect subagent (plan mode) → spec.md → user approves
        │
        ▼
   Developer subagent(s) in the worktree (backend-dev / frontend-dev / devops)
        │
        ▼
   Code reviewer subagent(s) (max 3 iterations)
        │
        ▼
   QA subagent (pytest + vitest + Playwright, verifies Acceptance Criteria)
        │
        ▼
   Open PR via gh pr create → post [H-xxx] comments
        │
        ▼
   Report to user → merge only with explicit approval
```

### Flags

- `--quick` — skip the architect/spec phase.
- `--backend-only` — only backend development.
- `--frontend-only` — only frontend development.
- `--serial` — run backend then frontend sequentially (default is parallel).
- `--qa` — run the dedicated QA gate before opening the PR.

---

## Hard rules

- **NEVER** continue the previous role for a new task.
- **NEVER** mix roles in one task.
- **NEVER** create a DB model without a migration.
- **NEVER** write an endpoint without tests.
- **NEVER** commit without explicit user approval.
- **ALWAYS** use trailing slash in FastAPI endpoints (`/items/`, not `/items`).
- **ALWAYS** run tests before reporting done.

---

## Required context (read before every task)

1. `PROJECT_CONTEXT.md` — stack, feature status, blockers, API inventory
2. `.agent/BACKLOG.md` — current sprint
3. `.agent/BLOCKERS.md` — active blockers
4. `.agent/SESSION_LOG.md` — recent sessions
5. The relevant role skill in `.kimi-code/skills/<role>/SKILL.md`
6. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md) (before code changes)

---

## Post-work updates

After finishing any task:

1. Update `.agent/SESSION_LOG.md`.
2. Update `.agent/BACKLOG.md` if the task is from the sprint.
3. Update `.agent/BLOCKERS.md` if a new blocker appeared.
4. Update `PROJECT_CONTEXT.md` if architecture changed.

---

## Permissions

**Allowed:**
- `make *`, `pytest *`, `alembic *`, `ruff *`
- `git status`, `git diff`, `git log`, `git worktree *`, `git commit *` (feature branches only)
- `npm *`, `npx *`
- `docker *`, `kubectl *`, `helm *`
- `gh workflow run *`, `gh run *`

**Forbidden:**
- `rm -rf *`
- `git push --force *`
- `git reset --hard *`
- `DROP *`, `truncate *`

---

## Before push

Run `make pre-push` (lint + unit tests + E2E) before pushing a feature branch.

Push rules:
- Pushing `feature/*` and `bugfix/*` branches to origin is auto-approved via permission rules in `~/.kimi-code/config.toml`.
- Pushing to `main` requires explicit user approval (permission rule uses `decision = "ask"`).

CI runs the E2E suite on the `promelectron-test` environment after deploy.

---

## See also

- [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) — language rule, retry policy, context size handling
- [Rule: Planning & Definition of Done](.kimi-code/rules/planning.md) — task format, prioritization, Definition of Done
- [Rule: Known Pitfalls](.kimi-code/rules/known-pitfalls.md) — real issues that have already happened
