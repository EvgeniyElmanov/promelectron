---
name: context-sync
description: >
  Synchronize and update Promelectron project context files.
  Analyzes git history, test status, codebase changes, and active blockers
  to update PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, and SESSION_LOG.md.
  Use when returning to the project after a break, when context files seem stale,
  before starting a new sprint, or for project health checks.
type: prompt
whenToUse: When the user asks to sync context, update context, check project status, or after a long pause.
arguments: "[--full] [--backlog-only] [--blockers-only] [--quick]"
disableModelInvocation: false
---

# /context-sync — Update Project Context

Synchronize `PROJECT_CONTEXT.md`, `BACKLOG.md`, `BLOCKERS.md` with reality.

---

## Step 1: Read Current State

Read:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. `.agent/PLANNING_HANDOFF.md` if exists

Record `last_update` from PROJECT_CONTEXT.md frontmatter.

---

## Step 2: Analyze Git History

```bash
git log --since="<last_update>" --oneline --no-merges
git log --oneline -30
```

Look for:
- New features (`feat:`)
- Fixes (`fix:`)
- Refactors (`refactor:`)
- Infra changes (`infra:`, `deploy:`)
- New migrations

---

## Step 3: Check Test Status

```bash
cd backend && pytest --tb=no -q 2>/dev/null || echo "Backend tests not runnable"
cd frontend && npm test -- --run 2>/dev/null || echo "Frontend tests not runnable"
```

---

## Step 4: Scan Blockers

For each blocker in `BLOCKERS.md`:
- grep the code — maybe already fixed?
- check deadlines > 2 days → mark escalated

---

## Step 5: Check for New Blockers

```bash
cd backend && alembic current 2>/dev/null || echo "Alembic issue"
cd backend && python -c "from src.app.main import app" 2>/dev/null || echo "Import error"
```

New blockers:
- Migration fails
- Tests fail on main
- CI workflow broken
- Missing env var in `.env.example`

---

## Step 6: Update PROJECT_CONTEXT.md

Update frontmatter:
```yaml
---
sprint: "<current>"
sprint_dates: "<dates>"
last_update: "<today>"
last_commit: "<hash>"
commit_message: "<message>"
blockers_count: <N>
blockers_p0: <N>
blockers_p1: <N>
backend_tests: "<X/Y>"
frontend_tests: "<X/Y>"
e2e_tests: "<X/Y>"
---
```

Update sections:
- What works now
- What is in progress
- Active blockers

Append a brief changelog at the bottom.

---

## Step 7: Update BACKLOG.md

For each sprint task:
- Code exists? grep
- Tests exist? find
- Routes registered? check main.py
- Frontend linked? check views/router/API calls
- Env vars set? check config.py, .env.example

Mark `[x]` only with evidence (commit or file). Add `(commit: abc1234)` when marking done.

---

## Step 8: Update BLOCKERS.md

- Move resolved blockers to "Resolved"
- Update deadlines
- Mark escalated (>2 days)
- Add new blockers from Step 5

---

## Step 9: Report

Report:
- What was updated
- Key changes since last_update
- Test results
- New/resolved/escalated blockers
- Sprint readiness

---

## Rules

- Evidence first — only facts from code and git.
- Do not delete completed tasks — move to "Completed".
- Date every status change.
- Preserve history — append-only changelog.
- If BACKLOG.md conflicts with code, code wins.
