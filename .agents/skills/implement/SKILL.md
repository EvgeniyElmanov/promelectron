---
name: implement
description: Full development cycle (Spec-Driven). Fetch the task (GitHub Issue or free text), isolate it in a git worktree, write a spec via the architect agent, develop backend/frontend in parallel, review in parallel, run QA, open a PR — and move the GitHub Project card through its status columns as it goes.
argument-hint: "<issue#|gh-5|task text> [--quick] [--backend-only] [--frontend-only] [--serial] [--qa]"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(jq *) Bash(mkdir *) Bash(ls *) Bash(make *)
---

# /implement — Full Development Cycle (Spec-Driven)

Pipeline: **fetch task → worktree → Spec (architect) → parallel Dev (Plan → Approve → Execute)
→ parallel Review → QA → PR.**
Each task runs in its **own git worktree** (`.worktrees/<task-id>`) with a durable coordination
plane in `.agent/runs/<task-id>/` (see the `pipeline-workspace` skill). Read-only phases (research,
first-pass review) **fan out into parallel sub-agents**.

If the task comes from a **GitHub Issue**, its card on the **GitHub Project** board is moved
through status columns as work progresses (see the `github-project` skill). **The internal
architect/review/QA loops never move the card** — only `start → In Progress` and
`PR opened → In Review` do.

## Flags
- `--quick` — skip the architect/spec phase (only for trivial, unambiguous tasks)
- `--backend-only` / `--frontend-only` — restrict development to one side
- `--serial` — backend then frontend sequentially (default is parallel)
- `--qa` — run the QA gate (Step 6) before the PR (otherwise QA is light/skipped)

---

## Step 1: Parse input & fetch the task

Record the repo root: `PROJECT_ROOT="$(git rev-parse --show-toplevel)"`. Parse flags; the rest is
the task identifier.

Check GitHub CLI access up front — issue linking and board automation depend on it:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

If either fails — stop and ask the user to run `gh auth login` or grant the `project` scope.

**If a GitHub Issue** (input is a number `5`, `#5`, `gh-5`, or an issue URL):
1. Extract the issue number `<N>`. `task-id` = `gh-<N>`.
2. Fetch it: `gh issue view <N> --json number,title,body,comments,url,labels`.
3. Create `.agent/runs/gh-<N>/review/` and write `task.md` (GitHub-Issue format from the
   `pipeline-workspace` skill). Record the current Project status in `task.md`.

**If free text** (no issue reference):
1. Generate `task-id` — short kebab-case slug (e.g. `add-product-filters`).
2. **Reuse** `.agent/runs/<task-id>/task.md` if it already exists (handed off from `/brainstorm`
   or `/backlog-pick`); otherwise create it (free-text format).
3. Force `--quick` only if the task is genuinely trivial — otherwise still spec it.

From here `<task-id>` is the issue id (`gh-<N>`) or the slug.
   The full issue lifecycle — labels, comments, closing **with evidence**, and the label-based
   fallback when the Project scope is missing — is `ai-launcher/CONVENTIONS.md` §8.


```bash
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"
```

---

## Step 1b: Occupy the item on the launch board

**Before** the worktree exists — the board is how several agent sessions avoid taking the
same work. In `ai-launcher/BOARD.md`:

1. Determine the item's **locks** from the files the task will touch — the table lives in
   `.agents/conventions/task-locks.md`. Take *every* lock the work touches, not just the main one.
2. **A lock already held by another item in «🔵 В работе» means STOP.** Say so to the user and let
   them decide; do not "work carefully alongside".
3. Flip the item to 🔵, add a row to «🔵 В работе» (issue, locks, branch `feature/<task-id>`), and
   recount the «🔒 Замки» block.
4. The board is edited **only in the repo root on `main`**, by name, never from the worktree:
   ```bash
   git -C "$PROJECT_ROOT" add ai-launcher/BOARD.md
   ```
   Run `python3 scripts/check-board.py` before committing — it verifies the board's form, its
   buttons and the prompt↔issue cross-links (rules: `ai-launcher/CONVENTIONS.md`).

Free-text task with no issue? Then there is no board item — skip this step, and say once that the
work is invisible to the board and sessions views until an issue exists.

---

## Step 2: Create the isolated worktree

Do this **before** any agent touches code, in normal (non-plan) mode — `git worktree add` is a
disk mutation plan mode blocks.

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" worktree add "$WORKTREE" -b feature/<task-id> origin/main
```

- **Always branch from `origin/main`.** Never from the current branch.
- If the worktree already exists (re-run), reuse it — check `git -C "$PROJECT_ROOT" worktree list`.
- A worktree is a fresh checkout: copy gitignored local files the build needs. Honor
  `.worktreeinclude` if present, else copy `.env`/`backend/.env`/`frontend/.env` when they exist.

**→ Move the Project card now (GitHub Issue tasks only).** Load the `github-project` skill and set
status `start → In Progress` (idempotent; skip if already there or further along). For free-text
tasks, skip silently.

---

## Step 3: Architect / Spec phase (SKIP if --quick)

The spec is written by the **`architect` agent** — you (orchestrator) only drive the loop and talk
to the user. Do not write the spec yourself.

### 3.1 Research fan-out (parallel, optional)
For non-trivial tasks, launch read-only research sub-agents (`general-purpose`) concurrently in a
single message — one per axis that applies (libraries, best-practices, codebase integration) —
each writing `AGENT_DIR/research/<axis>.md`. Skip for small internal changes.

### 3.2 Invoke the architect
```
Write the technical specification (Spec-Driven Development).
AGENT_DIR (coordination, absolute): <AGENT_DIR>
WORKTREE (code to explore, absolute): <WORKTREE>
Read AGENT_DIR/task.md. Read AGENT_DIR/research/*.md if present and synthesize into research.md.
Load context in parallel. Brainstorm 2–3 approaches. Produce AGENT_DIR/spec.md per your template.
If a requirement is ambiguous and changes the design, set Status: NEEDS_CLARIFICATION and list
questions under "Clarifications Needed" — do NOT guess.
```

### 3.3 Clarification loop
Read `AGENT_DIR/spec.md`.
- **If `Status: NEEDS_CLARIFICATION`** (or the recommended approach is a consequential choice the
  user should own): use `AskUserQuestion`, append answers to `## Clarifications` in `task.md`, then
  re-invoke the architect ("User answered — see task.md. Update spec.md, set Status: READY when
  nothing blocking remains."). Repeat until `READY`.
- **If `Status: READY`:** show a tight summary — chosen approach, **API Contract**, Must-haves, and
  the **Parallelization Plan** (will BE and FE run concurrently?).

Tell the user **"Spec ready. Start implementation?"** and **wait for confirmation.**

---

## Step 3.5: GitHub Issue Linking (before development)

Always link a GitHub Issue before development starts and move the Project board on phase
boundaries: spec approved → In progress, PR open → In review, merged → Done.

1. Check for an existing `github_issue` in `AGENT_DIR/task.md`. If present — **reuse it; never
   create a duplicate issue for the same task-id** (idempotency).
2. If missing — draft an issue from the spec/task description, **confirm it with the user first**
   (no silent publish: always ask before creating a GitHub Issue), then run:
   ```bash
   python scripts/implement-pipeline.py create-issue <task-id> --status in-progress
   ```
3. Once the spec is approved, make sure the board status is `In progress`:
   ```bash
   python scripts/implement-pipeline.py set-status <task-id> in-progress
   ```

---

## Step 4: Development — Plan → Approve → Execute (PARALLEL by default)

Read `Components Affected` and `Parallelization Plan` from `spec.md`. All code work targets
`WORKTREE` (use `git -C`, `make -C`, explicit paths — a sub-agent's `cd` does not persist).

Development is split into three phases: **Plan → Approve → Execute**. A developer agent **does not
write code without an approved plan**.

### Step 4a: Plan — developer writes PLAN.md

Launch the required developer roles with the task to **only write a plan**, without changing code.
Each role creates `$WORKTREE/PLAN.md` (a single shared one if serial; one per side —
`PLAN.backend.md` / `PLAN.frontend.md` — if parallel). The plan contains:

1. **Goal** — one sentence.
2. **Steps** — a numbered list: what changes, in which order, verification after each step.
3. **Risks / Open questions** — what could go wrong.

No production code, no migrations at this phase. After all roles finish, read the plan(s).

### Step 4b: Approve — auto or human

The orchestrator evaluates the plan(s) against the **auto-approve** criteria. A plan is
auto-approved if **all** conditions hold:

1. Only one side is affected OR backend and frontend have independent plans without
   cross-dependencies.
2. ≤ 5 Must-haves / Acceptance Criteria in the spec.
3. ≤ 4 major steps in the plan.
4. No auth / payments / PII / uploads / orders / webhooks (extended security scope).
5. No external integrations (1C, YooKassa, CDEK, Telegram, external APIs).
6. All risks are marked LOW or a standard rollback is described.

If the plan is auto-approved → Step 4c. If **any** criterion fails — show the user a brief summary
of PLAN.md (Goal, Steps, Risks) and ask **«approve the plan / revise?»**. On revision go back to
Step 4a. On approval proceed to Step 4c.

> **Don't skimp on human approval:** if the plan touches money, security, public API, or critical
> infrastructure — always show it to the user, even if it formally passes auto-approve.

### Step 4c: Execute — implement the approved plan

**If both sides are affected and independent (and no `--*-only`/`--serial`):** launch `backend-dev`
and `frontend-dev` **in the same message** so they run concurrently. They edit disjoint trees
(`backend/` vs `frontend/`) and both build against the spec's **API Contract** (frontend mocks the
API until the endpoint lands). A `devops` role, if needed, runs after they finish.

Developer prompt:
```
Implement your part of the task.
AGENT_DIR (absolute): <AGENT_DIR>      WORKTREE (do ALL code work here, absolute): <WORKTREE>
Read AGENT_DIR/task.md and AGENT_DIR/spec.md. Honor every D-number exactly. Read WORKTREE/PLAN.md —
the approved plan — and implement strictly per it; if it becomes unworkable mid-flight, stop,
report, revise the plan, and get re-approval before continuing. Build strictly against the API
Contract. Backend: model → schema → service → route → tests. Frontend: service → composable
→ component → page → tests. Target WORKTREE with explicit paths (git -C, make -C, uv --directory).
MANDATORY before done: run lint + tests in WORKTREE, fix all issues, commit to feature/<task-id>.
```

**If only one side, or `--serial`/`--backend-only`/`--frontend-only`:** run the relevant
developer(s); `--serial` runs backend first, then frontend.

---

## Step 4.5: API Contract Validation (backend ↔ frontend)

Skip if the feature touches only backend or only frontend. Otherwise — **before launching reviewer
sub-agents** the orchestrator personally verifies that backend and frontend converged on the
contract from `AGENT_DIR/spec.md`:

1. Extract changed/new endpoints from the backend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'backend/src/app/api/*.py' | grep -E '^\+.*@(router|.*)\.(get|post|put|patch|delete)'
   ```
2. Extract API calls from the frontend diff:
   ```bash
   git -C "$WORKTREE" --no-pager diff origin/main...HEAD -- 'frontend/src/api/*' | grep -E '^\+.*(get|post|put|patch|delete)\('
   ```
3. Check every endpoint from the spec's `API Changes`:
   - **path** matches, including **trailing slash** (`/items/`, not `/items`)
   - **HTTP method** matches
   - **request fields** (body/params/query) match the Pydantic schema
   - **response fields** the frontend actually reads are present in the response schema
4. On any mismatch — record it in `AGENT_DIR/review/findings.md` as
   `[F-xxx] CRITICAL | API Contract` with status `OPEN` and send the respective developer back to
   fix it **before** Step 5.
5. No mismatches — proceed to Step 5.

This step catches the "backend and frontend diverged on the contract in parallel" class of bugs,
which is cheaper to fix before review than after it.

---

## Step 5: Code review loop — PARALLEL (max 3 iterations)

**This loop never touches the GitHub Project board** (agent review ≠ board "In Review").

Each iteration:
1. **Scope from what changed.** Backend + frontend → **two** `code-reviewer` agents in one message
   (scoped `backend/` and `frontend/`), writing `review/findings-backend.md` /
   `review/findings-frontend.md`. For security-sensitive work (auth, payments, orders) add
   `security-reviewer` to the same parallel batch. Single side → one `code-reviewer` →
   `review/findings.md`.
   ```
   Review the code changes (scope: <backend|frontend|all>).
   AGENT_DIR (absolute): <AGENT_DIR>     WORKTREE (read diff here, absolute): <WORKTREE>
   Read the diff: git -C <WORKTREE> diff origin/main...HEAD
   Read AGENT_DIR/spec.md. Check against Decisions (D-numbers), API Contract, Acceptance Criteria —
   violations = CRITICAL. Write review/findings<-scope>.md. Do NOT edit source.
   ```
2. **Merge** partials into `review/findings.md`: `Status` = `FIXES_NEEDED` if any sub-report needs
   fixes, else `APPROVED`; renumber findings unique across scopes; preserve Human Decisions.
3. **If `APPROVED`** → Step 6.
4. **If `FIXES_NEEDED`:** show the user the findings summary + any `[H-xxx]` items; wait for the
   user on H-items and record the decision in `spec.md`; invoke the affected developer(s) — in
   parallel if both sides have open findings — to fix OPEN findings (mark each `FIXED`, re-run
   tests, commit). Repeat from iteration start.
5. **After iteration 3 still `FIXES_NEEDED`:** show remaining open findings, ask the user how to
   proceed. Do not continue automatically.

---

## Step 6: QA gate (run if `--qa`, else light)

Invoke `qa`:
```
Run tests and verify acceptance criteria.
AGENT_DIR (absolute): <AGENT_DIR>     WORKTREE (absolute): <WORKTREE>
Read AGENT_DIR/spec.md. Run backend + frontend tests in WORKTREE (parallel where possible) and E2E
if UI. Verify each Acceptance Criterion and Scenario. Write review/test-findings.md.
```
Read `review/test-findings.md`. **`TESTS_PASSED`** → Step 7. **`TESTS_FAILED`** → show failures,
invoke the affected developer(s) to fix, then **return to Step 5** (code changed → re-review).
Max 2 QA iterations, then escalate to the user.

Without `--qa`, rely on the developers' own test runs and skip the dedicated gate.

With `--qa` (or to re-run QA for an already-built task), invoke the standalone **`qa-gate`
command**: it locates the task's coordination plane and worktree and runs the full QA check
(pytest + vitest + Playwright) against the Acceptance Criteria from `spec.md`. If the gate fails —
fix and repeat; never open a PR with a red QA gate.

---

## Step 7: Create the Pull Request

**Delegate PR creation to the `ship` command** — it is the single copy of the PR logic: it runs
the pre-push checks, pushes `feature/<task-id>`, creates the PR via `gh pr create`, posts open
`[H-xxx]` items from `AGENT_DIR/review/findings.md` as PR comments, and moves the Project card to
`In Review` (the human-review signal; idempotent, never regresses).

**Do not set Done** — this pipeline does not merge; leave Done to the human / merge automation.

If ship fails (e.g. pre-push checks are red), stop and report the error — never open a PR with
failing checks.

Report to the user: PR URL · worktree path (kept for follow-up) · review iterations · board status
now `In Review` (or "board not updated — task is free-text / scope missing") · "After merge → test
deploys via GitHub Actions; prod = manual workflow with environment=prod."

---


### Board: hand the lock back

After the PR is open, update `ai-launcher/BOARD.md` in the repo root (not the worktree): the item
stays 🔵 with its PR number until merge — that is what keeps the lock honest. **On merge** the row
leaves «🔵 В работе», the block with the button is removed, and the «🔒 Замки» block is recounted.

⚠️ If the item also has a row in «⏰ Ждут условия», **merged is not done**: that row stays until the
condition is met and the check has actually been performed. Say it to the user out loud instead of
closing the item quietly — this is exactly the tail that gets lost.

---

## Rules
- **Never merge automatically** — a human reviews and merges.
- **Never push to main** — always via PR.
- **Agent review never moves the board.** Only `start → In Progress` (Step 2) and
  `PR opened → In Review` (Step 7) move the card. Done is left to merge.
- **Always link a GitHub Issue before development** (Step 3.5) and move the card on phase
  boundaries: spec approved → In progress, PR open → In review, merged → Done.
- **Idempotency:** never create a duplicate issue for the same `task-id`; reuse `github_issue`
  from `task.md`.
- **No silent publish:** always ask the user before creating a GitHub Issue.
- **Don't skimp on human approval:** plans touching money, security, public API, or critical
  infrastructure always go to the user, even when they formally pass auto-approve.
- **Spec first:** no developer runs before `spec.md` is `READY` (except `--quick`).
- **Plan before code:** no developer writes code before its PLAN.md is approved (Step 4b).
- The architect writes the spec; developers/reviewers/QA never rewrite it (the orchestrator may
  append Human-Decision outcomes).
- **Parallel by default:** batch independent agents into one message (BE‖FE dev, BE‖FE‖security
  review). Serialise only when streams share files or `--serial` is set.
- **One worktree per task**; `.agent/runs/<task-id>/` is the durable coordination plane (gitignored,
  separate from the committed `docs/` planner).
- Developer marks findings `FIXED`; only the reviewer marks `VERIFIED`. Reviewer/QA never edit source.
- Max 3 review + 2 QA iterations, then escalate.
