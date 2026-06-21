# Rule: planning

Rules for maintaining project plans, roadmaps, task prioritization, and the Definition of Done.

## Single Source of Truth

`.agent/PLANNING_HANDOFF.md` is the only authoritative plan. `ROADMAP.md` is historical reference only.

- When updating plans, always edit `.agent/PLANNING_HANDOFF.md` first.
- If `ROADMAP.md` contradicts `.agent/PLANNING_HANDOFF.md`, `.agent/PLANNING_HANDOFF.md` wins.
- After updating `.agent/PLANNING_HANDOFF.md`, update `ROADMAP.md` only if explicitly requested.

## Task Format

Every task in `.agent/PLANNING_HANDOFF.md` and `.agent/BACKLOG.md` should follow this format:

```markdown
- [ ] **ID-XXX** Task title (S|M|L) — risk: low|medium|high
  - **Why:** Business or technical justification
  - **What:** Concrete deliverables
  - **Depends on:** IDs of blocking tasks
  - **Blocked by:** IDs of tasks that block this one
  - **Acceptance:** How to verify completion
```

## Status Definitions

| Status | Symbol | Meaning |
|--------|--------|---------|
| Not started | `[ ]` | No code written |
| In progress | `[/]` | Active work, not committed |
| In review | `[?]` | PR open or pending review |
| Done | `[x]` | Merged to main, verified |
| Blocked | `[!]` | External dependency or blocker |
| Deferred | `[-]` | Intentionally postponed |

## Prioritization Matrix

Rank tasks by:

1. **Production blocker** — breaks live environment (P0)
2. **Security risk** — vulnerability or data exposure (P0)
3. **Regression** — breaks existing functionality (P1)
4. **Feature blocker** — blocks other planned work (P1)
5. **Business value** — directly impacts users/revenue (P2)
6. **Tech debt** — slows future development (P3)

## Sprint Boundaries

- A sprint is 1 week max.
- Each sprint has at most 1 P0 and 2 P1 tasks.
- Everything else is P2/P3 and can spill over.
- At sprint end, update `.agent/PLANNING_HANDOFF.md` and `.agent/BACKLOG.md` with:
  - What was completed
  - What was not and why
  - New blockers discovered
  - Next sprint proposal

## Dependency Rules

- Never start a task whose dependencies are not Done.
- If a dependency is Blocked, escalate immediately.
- Document cross-team dependencies (infra, design, 3rd party APIs).

## Assumption Tracking

Every estimate carries assumptions. Document them:

```markdown
**Assumptions:**
- MinIO is already deployed in K8s cluster (confirmed: yes)
- `API_BASE_URL` env var will be added by DevOps (owner: @devops)
- No schema changes needed for this task
```

When an assumption turns out false, re-estimate immediately.

## Definition of Done

A task is Done only when:

- [ ] Code is written and committed
- [ ] Tests pass (backend + frontend + E2E if UI)
- [ ] No new lint/security errors
- [ ] Feature works in local environment
- [ ] `.agent/BACKLOG.md` is updated with status
- [ ] No follow-up tasks created without explicit user approval
