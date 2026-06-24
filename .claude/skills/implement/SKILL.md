---
name: implement
description: Full development cycle (Spec-Driven). Fetch the task (GitHub Issue or free text), isolate it in a git worktree, write a spec via the architect agent, develop backend/frontend in parallel, review in parallel, run QA, open a PR — and move the GitHub Project card through its status columns as it goes.
argument-hint: "<issue#|gh-5|task text> [--quick] [--backend-only] [--frontend-only] [--serial] [--qa]"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(jq *) Bash(mkdir *) Bash(ls *) Bash(make *)
---

# /implement — Full Development Cycle (Spec-Driven)

Pipeline: **fetch task → worktree → Spec (architect) → parallel Dev → parallel Review → QA → PR.**
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

```bash
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"
```

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

## Step 4: Development — PARALLEL by default

Read `Components Affected` and `Parallelization Plan` from `spec.md`. All code work targets
`WORKTREE` (use `git -C`, `make -C`, explicit paths — a sub-agent's `cd` does not persist).

**If both sides are affected and independent (and no `--*-only`/`--serial`):** launch `backend-dev`
and `frontend-dev` **in the same message** so they run concurrently. They edit disjoint trees
(`backend/` vs `frontend/`) and both build against the spec's **API Contract** (frontend mocks the
API until the endpoint lands).

Developer prompt:
```
Implement your part of the task.
AGENT_DIR (absolute): <AGENT_DIR>      WORKTREE (do ALL code work here, absolute): <WORKTREE>
Read AGENT_DIR/task.md and AGENT_DIR/spec.md. Honor every D-number exactly. Build strictly against
the API Contract. Backend: model → schema → service → route → tests. Frontend: service → composable
→ component → page → tests. Target WORKTREE with explicit paths (git -C, make -C, uv --directory).
MANDATORY before done: run lint + tests in WORKTREE, fix all issues, commit to feature/<task-id>.
```

**If only one side, or `--serial`/`--backend-only`/`--frontend-only`:** run the relevant
developer(s); `--serial` runs backend first, then frontend.

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

---

## Step 7: Create the Pull Request

All git ops target the worktree.

1. Push: `git -C "$WORKTREE" push -u origin feature/<task-id>`
2. Create the PR:
   ```bash
   gh pr create --base main --head feature/<task-id> \
     --title "<concise description>" \
     --body "$(cat <<'EOF'
   ## Summary
   <what was done>

   ## Spec
   .agent/runs/<task-id>/spec.md — chosen approach + API contract

   ## Changes
   <changed files/components>

   ## Test Results
   - Backend: pytest X/Y · Frontend: vitest X/Y

   ## Acceptance Criteria
   <checked list from test-findings.md>

   Closes #<N>   <!-- only for GitHub Issue tasks -->
   EOF
   )"
   ```
   For a GitHub Issue task, include `Closes #<N>` so merging closes the issue.
3. **→ Move the Project card now (GitHub Issue tasks only).** Load the `github-project` skill and
   set status `pr_opened → In Review` (the human-review signal). Idempotent; never regress.
   **Do not set Done** — `/implement` does not merge; leave Done to the human / merge automation.
4. If `review/findings.md` has Human Decisions still open, post each `[H-xxx]` as a PR comment
   (`gh pr comment`). These are the only review comments posted.
5. Report to the user: PR URL · worktree path (kept for follow-up) · review iterations · board
   status now `In Review` (or "board not updated — task is free-text / scope missing") ·
   "After merge → test deploys via GitHub Actions; prod = manual workflow with environment=prod."

---

## Rules
- **Never merge automatically** — a human reviews and merges.
- **Never push to main** — always via PR.
- **Agent review never moves the board.** Only `start → In Progress` (Step 2) and
  `PR opened → In Review` (Step 7) move the card. Done is left to merge.
- **Spec first:** no developer runs before `spec.md` is `READY` (except `--quick`).
- The architect writes the spec; developers/reviewers/QA never rewrite it (the orchestrator may
  append Human-Decision outcomes).
- **Parallel by default:** batch independent agents into one message (BE‖FE dev, BE‖FE‖security
  review). Serialise only when streams share files or `--serial` is set.
- **One worktree per task**; `.agent/runs/<task-id>/` is the durable coordination plane (gitignored,
  separate from the committed `.agent/` planner).
- Developer marks findings `FIXED`; only the reviewer marks `VERIFIED`. Reviewer/QA never edit source.
- Max 3 review + 2 QA iterations, then escalate.
