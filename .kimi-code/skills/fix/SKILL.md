---
name: fix
description: >
  Bug fix workflow for Promelectron. Use when the user reports a bug, error, crash, exception, test failure, or broken functionality
  in backend, frontend, or infrastructure. Analyzes the bug, determines the correct role, reproduces with a minimal test,
  fixes the root cause (not symptoms), runs tests, checks the golden path if affected, and reports results.
type: prompt
whenToUse: When the user reports a bug, crash, failing test, regression, or anything that "does not work". Also triggers on words like fix, bug, broken, error, exception, fail, failing, regression.
arguments: "<bug description> [--backend] [--frontend] [--infra] [--e2e]"
disableModelInvocation: false
---

# /skill:fix — Bug Fix Workflow

Fix a bug systematically: analyze → reproduce → fix → test → verify.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule. All Russian-language requirements and subagent prompt preambles live there.

---

## Step 1: Analyze and Route

Output:
```
🔄 Role reset. Analyzing the bug...
```

Determine the role by bug type:

| Bug type | Role |
|----------|------|
| API error, 500, DB, migration, race condition | `backend-dev` |
| UI broken, CSS, router, form, frontend validation | `frontend-dev` |
| Docker, Helm, CI/CD, deploy, secrets, nginx | `devops` |
| Playwright test fails, selector missing | `e2e-tester` |

If unsure — ask the user.

Announce:
```
🎯 Role: <ROLE> (bug fix)
```

---

## Step 1b: Context Size Check (Kimi K2.7)

If the bug fix involves a task directory in `.agent/runs/<task-id>/`, follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check.

---

## Step 1c: Retry Policy

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Retry Policy when launching subagents.

---

## Step 2: Read Context

Read:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. `.kimi-code/skills/<ROLE>/SKILL.md`
6. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)
7. [Rule: Golden Path](.kimi-code/rules/golden-path.md) if the bug touches cart, checkout, auth, payment, orders

---

## Step 3: Reproduce

Find the bug:
- `git log --oneline -10` — what changed recently?
- `git diff` — any uncommitted changes?
- `grep` for error keywords.

Reproduce:
- **Backend:** write a minimal test that fails because of the bug.
- **Frontend:** describe reproduction steps or write a unit test.
- **E2E:** run the specific test: `npx playwright test <spec>`.

Rule: if you cannot reproduce, ask the user for details. Do NOT fix blindly.

---

## Step 4: Fix Root Cause

Diagnose:
- Recent regression or new bug?
- Edge case (null, empty list, division by zero, race condition)?
- Wrong type? Missing validation?

Fix:
- Fix the **cause**, not the **symptom**.
- Do NOT wrap everything in try/except.
- If you change a model → create an Alembic migration.
- If you change an API contract → update the frontend API layer.

Use a git worktree if there is any risk of interfering with other work:
```bash
git worktree add .worktrees/fix-<slug> -b bugfix/<slug>
cd .worktrees/fix-<slug>
```

---

## Step 5: Test

1. Write/update a test that would have failed before the fix and passes now.
2. Run module tests: `pytest tests/test_<module>.py -x` or `npm test -- <pattern>`.
3. Run lint: `ruff check` / `npm run lint`.
4. If golden path affected → verify the corresponding scenario.

---

## Step 6: Report

Update `.agent/SESSION_LOG.md`:
```markdown
## <YYYY-MM-DD> — Fix: <short bug description>
- **Role:** <ROLE>
- **Root cause:** ...
- **Fix:** ...
- **Files:** `<file1>`, `<file2>`
- **Tests:** ...
- **Golden path checked:** yes/no
- **Regression risk:** low/medium/high
- **Estimated tokens:** <N> (if task dir exists)
```

Update `.agent/BACKLOG.md` if the bug was from the sprint.

Report to the user:
- Root cause
- Fix
- Files changed
- Test results

---

## Anti-Patterns

- ❌ Fix the symptom instead of the cause.
- ❌ Remove a failing test instead of fixing the code.
- ❌ Add print/console.log for debugging.
- ❌ Ignore a flaky test.
- ❌ Commit without user approval.
