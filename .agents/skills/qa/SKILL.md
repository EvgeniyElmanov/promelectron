---
name: qa
description: Standalone QA stage for a pipeline task. Locates the task's coordination plane (.agent/runs/<task-id>/) and worktree (.worktrees/<task-id>/), then drives the qa agent to run backend pytest + frontend vitest (parallel where possible) and Playwright E2E when the change touches UI/API, verifies every Acceptance Criterion and Scenario from spec.md, and writes review/test-findings.md. This is the extracted, runnable version of /implement Step 6. The qa agent never edits source; this skill never moves the GitHub Project board.
argument-hint: "<issue#|gh-5|task-id|slug> [--e2e]"
disable-model-invocation: true
allowed-tools: Read Bash(git *) Bash(gh *) Bash(ls *) Bash(mkdir *)
---

# /qa — Standalone QA stage

Run the **QA gate** for a single task and write its results to
`.agent/runs/<task-id>/review/test-findings.md`. This is the standalone form of `/implement`
**Step 6** — use it to (re-)check a task that was already specced and built, without re-running the
whole pipeline.

The actual testing is done by the existing **`qa` agent** (`subagent_type=qa`). You (orchestrator)
only locate the workspace, invoke the agent, and report. The qa agent **never edits source code** —
failures come back as findings for the developer loop.

> This skill keeps the two-stage design lightweight: there is **no** mandatory plan-mode human gate
> and **no** hurl/grpcurl/qa-psql tooling. Backend tests use **pytest**, frontend uses **vitest**,
> E2E uses **Playwright** — the project's real tooling (see the `testing-conventions` skill).

## Input: `<issue#|gh-5|task-id|slug> [--e2e]`

- The argument identifies the task. Resolve it to a `task-id` (see the `pipeline-workspace` skill):
  - a GitHub Issue reference (`5`, `#5`, `gh-5`, or an issue URL) → `task-id = gh-<N>`;
  - anything else → treat it as the kebab-case `task-id`/slug directly.
- `--e2e` — force the Playwright E2E suite to run even if the UI/API change is not obvious. By
  default the qa agent decides E2E based on what changed (UI or API → run E2E).
- If no argument is given, ask the user which task to QA (or `git -C "$PROJECT_ROOT" worktree list`
  to show candidates).

## Step 0: Locate the workspace & preflight

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"
mkdir -p "$AGENT_DIR/review"
```

- **If `$AGENT_DIR` is missing** — stop and tell the user (in Russian) to run `/architect` or
  `/implement` first; there is nothing to QA without a coordination plane.
- **If `$WORKTREE` is missing** — stop and tell the user the worktree was removed (likely merged);
  re-create it with `/implement <task-id>` or check `git -C "$PROJECT_ROOT" worktree list`.
- **If `$AGENT_DIR/spec.md` is missing** — warn that there is no spec, so Acceptance-Criteria
  verification will be best-effort; the qa agent still runs the test suites. Offer to run
  `/architect <task-id>` first to produce a spec.

Never write into the **committed** `docs/` planner — only into `.agent/runs/<task-id>/` (the
gitignored coordination plane). Never `git add .agent/runs/`.

## Step 1: Invoke the qa agent (single agent — it parallelises internally)

Invoke `subagent_type=qa`, pointed at the two absolute paths. The agent reads `spec.md`, runs the
backend and frontend suites (parallel where possible), runs Playwright E2E if the change touches
UI/API, checks every Acceptance Criterion and Scenario, and writes the findings file.

```
Run the QA stage for this task. Do NOT modify source code.
AGENT_DIR (coordination, absolute): <AGENT_DIR>
WORKTREE (code to test, do ALL work here, absolute): <WORKTREE>

Read AGENT_DIR/spec.md — Acceptance Criteria, Scenarios, and Must-haves. (If spec.md is absent,
run the suites anyway and verify what you can from task.md.)

Run the test suites in WORKTREE, in parallel where possible, with explicit paths (no persistent cd):
- Backend (if backend/ changed):   cd <WORKTREE>/backend && uv run pytest -x -v 2>&1
- Frontend (if frontend/ changed): cd <WORKTREE>/frontend && npm test 2>&1
- E2E (if UI or API changed[, or --e2e]): cd <WORKTREE>/tests/e2e && npm ci &&
  BASE_URL=https://promelectron-test.aidrivencode.ru npx playwright test --reporter=list 2>&1
  (Makefile equivalents from <WORKTREE>: make test-backend / test-frontend / test-e2e.)

Verify each Acceptance Criterion and Scenario from spec.md against the results.
Write AGENT_DIR/review/test-findings.md in the format from your agent definition:
- Status: TESTS_PASSED only if ALL suites pass AND all Acceptance Criteria are met; else TESTS_FAILED.
- Each failure becomes a finding: F- = agent-fixable defect, H- = needs a human decision.
- Include full pytest/vitest/playwright output for failing cases.
Return a short summary: pass/fail counts per suite and the list of F-/H-findings.
```

Pass `--e2e` through to the agent prompt when the user supplied it (force the E2E line).

## Step 2: Report (in Russian)

Read `$AGENT_DIR/review/test-findings.md` and report to the user **in Russian**:

- **Статус:** `TESTS_PASSED` или `TESTS_FAILED`.
- **Счётчики по наборам:** pytest X/Y, vitest X/Y, Playwright X/Y (пропущенные наборы — пометить
  «не запускались», напр. если backend не менялся).
- **Acceptance Criteria:** какие критерии выполнены / не выполнены.
- **Находки:** каждый **F-finding** (исправимый дефект — для разработчика) и **H-finding** (решение
  за человеком), кратко.
- **Путь к отчёту:** `.agent/runs/<task-id>/review/test-findings.md`.

If `TESTS_FAILED` **and** the task came from `/implement` (GitHub Issue / pipeline task), suggest
feeding the F-findings back into the developer loop — i.e. invoke `backend-dev`/`frontend-dev` on
the OPEN findings, then re-run `/qa <task-id>` (mirrors `/implement` Steps 5–6). Do **not** fix code
here yourself.

## Rules

1. **The qa agent never edits source** — it only verifies and writes findings. Fixes go through the
   developer agents.
2. **No board movement.** This QA stage does **not** move the GitHub Project card. Only `/implement`
   moves the board (`start → In Progress`, `PR opened → In Review`).
3. **Real tooling only** — pytest (backend), vitest (frontend), Playwright (E2E). Do not invent
   hurl/grpcurl/qa-psql; do not mock the database in backend tests (real test DB); external HTTP in
   backend tests is mocked via `respx`.
4. **`TESTS_PASSED` is strict** — only when every suite passes and every Acceptance Criterion is met.
5. **Workspace discipline** — read/write only under `.agent/runs/<task-id>/` and `.worktrees/<task-id>/`;
   never touch the committed `docs/` planner, never `git add .agent/runs/`.
6. **Lightweight gate** — no mandatory plan-mode human approval. Run the suites and report. (If the
   user explicitly wants to review/edit a test plan before execution, you may add a manual gate, but
   it is not required.)
