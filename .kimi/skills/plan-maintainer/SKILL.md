---
name: plan-maintainer
description: Maintain and evolve the project plan (.agent/PLANNING_HANDOFF.md and .agent/BACKLOG.md). Read codebase, assess task status, update priorities, and detect blockers.
argument-hint: "<action: analyze|update|propose|sprint-review>"
disable-model-invocation: false
---

# Plan Maintainer

Maintain `.agent/PLANNING_HANDOFF.md` and `.agent/BACKLOG.md` as the single source of truth for project execution.

## Capabilities

- **Analyze** — scan codebase and Git history to determine true task status
- **Update** — mark tasks done, blocked, or deferred based on evidence
- **Propose** — suggest next sprint or task sequence with justification
- **Sprint Review** — summarize what happened, what didn't, and why

## Commands

### `analyze`
```
Read .agent/PLANNING_HANDOFF.md → Read .agent/BACKLOG.md → git log --oneline -30 → scan key files → report discrepancies
```

Use when:
- User asks "What's the real status?"
- Before proposing a new sprint
- After a long pause in the project

### `update`
```
Read .agent/BACKLOG.md → verify specific task in code → edit status → write back
```

Use when:
- A task was completed in the current session
- A blocker was resolved
- New technical debt was discovered

### `propose`
```
Read .agent/BACKLOG.md → identify unblocked P0/P1 → estimate capacity → write sprint proposal
```

Use when:
- User asks "What should I do next?"
- Starting a new week/sprint
- Scope changed

### `sprint-review`
```
Read .agent/BACKLOG.md → git log --since="1 week ago" → compare planned vs actual → write review
```

Use when:
- End of sprint
- Retrospective
- User wants accountability

## Analysis Checklist

When analyzing task status, verify:

- [ ] **Code exists** — grep for function/component names
- [ ] **Tests exist** — grep for `test_` + task name
- [ ] **Routes registered** — check `main.py` or router includes
- [ ] **Frontend linked** — check views, router, API calls
- [ ] **Env vars set** — check `config.py`, `.env.example`, K8s manifests
- [ ] **CI covers it** — check `.github/workflows/` (if accessible)
- [ ] **Docs updated** — check `README.md`, `AGENTS.md`

Never rely on `ROADMAP.md` alone — it becomes stale.

## Update Rules

1. **Evidence first** — only mark `[x]` if you can point to a commit or file
2. **Link commits** — when marking done, add `(commit: abc1234)`
3. **Explain blocks** — when marking `[!]`, explain the exact blocker
4. **Date everything** — add `(updated: YYYY-MM-DD)` to status changes
5. **Preserve history** — don't delete old tasks; move them to "Completed" section

## Sprint Proposal Format

```markdown
## Sprint N — YYYY-MM-DD to YYYY-MM-DD

**Theme:** <one-line goal>
**Capacity:** <estimated hours or story points>

### P0 (Must)
- [ ] **ID-001** Title (M) — risk: medium

### P1 (Should)
- [ ] **ID-002** Title (S) — risk: low
- [ ] **ID-003** Title (M) — risk: low

### P2 (Could)
- [ ] **ID-004** Title (L) — risk: high

### Assumptions
- <list>

### Risks
- <list>
```

## Anti-Patterns

- ❌ Don't create tasks larger than 1 day of work
- ❌ Don't assign tasks to sprints without checking dependencies
- ❌ Don't hide blockers — escalate them
- ❌ Don't duplicate tasks between `.agent/PLANNING_HANDOFF.md` and `ROADMAP.md`
- ❌ Don't delete completed tasks — archive them
