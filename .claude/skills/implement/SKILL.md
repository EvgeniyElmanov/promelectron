---
name: implement
description: Full development cycle (Spec-Driven). Brainstorm + spec via the architect agent, then parallel backend/frontend development, parallel code review, QA loop, and Merge Request creation.
argument-hint: "<task description> [--quick] [--backend-only] [--frontend-only] [--serial]"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(mkdir *) Bash(ls *)
---

# /implement — Full Development Cycle (Spec-Driven)

Pipeline: **Brainstorm + Spec (architect) → parallel Dev → parallel Review → QA → MR.**

Flags:
- `--quick` — skip the architect/spec phase (only for trivial, unambiguous tasks)
- `--backend-only` — only invoke backend-dev
- `--frontend-only` — only invoke frontend-dev
- `--serial` — force backend then frontend sequentially (default is parallel)

## Step 1: Parse and Setup

Parse `$ARGUMENTS`:
- Extract task description (everything before flags)
- Note any flags present

Generate `<task-id>` — short kebab-case slug.
Examples: `add-product-filters`, `fix-cart-stock-check`, `onec-price-sync`

Create working directory and write task file:
```bash
mkdir -p .agent/<task-id>/review
```

`.agent/<task-id>/task.md`:
```markdown
# Task: <task-id>
## Description
<full task description>
## Flags
<active flags or "none">
## Clarifications
<appended here as the user answers them — newest at bottom>
```

---

## Step 2: Brainstorm + Spec Phase (skip if --quick)

The spec is written by the **`architect` agent** — you (the orchestrator) only drive the
loop and talk to the user. Do not write the spec yourself.

### 2a. Invoke the architect
Invoke `architect`:
```
Write the technical specification (Spec-Driven Development).
Task directory: .agent/<task-id>/
Read task.md first. Load context in parallel. Brainstorm 2–3 approaches.
Produce .agent/<task-id>/spec.md per your template.
If a requirement is ambiguous and changes the design, set Status: NEEDS_CLARIFICATION
and list questions under "Clarifications Needed" — do NOT guess.
```

### 2b. Clarification loop
Read `.agent/<task-id>/spec.md`.

- **If `Status: NEEDS_CLARIFICATION`** (or the recommended approach is a consequential
  choice the user should own):
  1. Use `AskUserQuestion` to ask the open questions + approach choice. Keep each question
     self-contained with the options the architect surfaced.
  2. Append the answers to the `## Clarifications` section of `task.md`.
  3. Re-invoke `architect`: "User answered — see task.md Clarifications. Update spec.md and
     set Status: READY when nothing blocking remains."
  4. Repeat until `Status: READY`.

- **If `Status: READY`:** show the user a tight summary — chosen approach, the **API
  Contract**, Must-haves, and the **Parallelization Plan** (will BE and FE run concurrently?).

Tell the user: **"Spec ready. Start implementation?"** and **wait for confirmation.**

---

## Step 3: Git Branch

```bash
git fetch origin
git checkout -b feature/<task-id> origin/main
```

---

## Step 4: Implementation — PARALLEL by default

Read `Components Affected` and `Parallelization Plan` from spec.md.

**If both backend and frontend are affected and `Parallelization Plan` says independent
(and neither `--backend-only`/`--frontend-only`/`--serial`):**
Launch `backend-dev` and `frontend-dev` **in the same message** so they run concurrently.
They edit disjoint trees (`backend/` vs `frontend/`) and both build against the spec's
**API Contract**, so there is no conflict — the frontend mocks the API until the backend
endpoint lands.

Prompt for each developer:
```
Implement your part of the task.
Task directory: .agent/<task-id>/
Read task.md and spec.md before starting. Build strictly against the API Contract.
Backend: model → schema → service → route → tests. Frontend: service → composable → component → page → tests.
Run your own tests + lint before finishing. Commit to feature/<task-id> with a descriptive message.
```

**If only one side is affected, or `--serial`/`--backend-only`/`--frontend-only`:**
run the relevant developer(s); for `--serial` run backend first, then frontend.

---

## Step 5: Code Review Loop — PARALLEL (max 3 iterations)

### Each iteration

1. **Determine scope** from what changed:
   - Backend + frontend changed → launch **two** `code-reviewer` agents **in one message**
     (one scoped to `backend/`, one to `frontend/`), writing `review/findings-backend.md`
     and `review/findings-frontend.md` respectively. For security-sensitive work (auth,
     payments, orders) add `security-reviewer` to the same parallel batch.
   - Single side → one `code-reviewer`, writing `review/findings.md`.

   Reviewer prompt:
   ```
   Review the code changes (scope: <backend|frontend|all>).
   Task directory: .agent/<task-id>/
   Read spec.md. Check against Decisions, API Contract, and Acceptance Criteria.
   Write results to review/findings<-scope>.md. Do NOT edit source.
   ```

2. **Merge** parallel reports into `review/findings.md`:
   - Overall `Status` = `FIXES_NEEDED` if any sub-report needs fixes, else `APPROVED`.
   - Combine findings, renumber so IDs are unique across scopes, preserve Human Decisions.

3. **If `APPROVED`** → go to Step 6.

4. **If `FIXES_NEEDED`:**
   - Show the user: findings summary + any `[H-xxx]` Human Decision items.
   - For H-items: wait for the user's decision, update spec.md with it.
   - Invoke the affected developer(s) — **in parallel** if both sides have open findings:
     ```
     Fix OPEN findings from review/findings.md for your scope.
     Task directory: .agent/<task-id>/
     Mark each fixed item FIXED with a Developer note. Re-run your tests.
     ```
   - Repeat from iteration start.

5. **After iteration 3, still FIXES_NEEDED:** show remaining open findings, ask the user
   how to proceed. Do not continue automatically.

---

## Step 6: QA Loop (max 2 iterations)

1. Invoke `qa`:
   ```
   Run tests and verify acceptance criteria.
   Task directory: .agent/<task-id>/
   Read spec.md. Run backend + frontend tests (in parallel where possible) and E2E if UI.
   Verify each Acceptance Criterion and Scenario. Write results to review/test-findings.md.
   ```

2. Read `.agent/<task-id>/review/test-findings.md`.

3. **If `TESTS_PASSED`** → go to Step 7.

4. **If `TESTS_FAILED`:**
   - Show the user the failures summary.
   - Invoke the affected developer(s) to fix OPEN items.
   - Return to **Step 5** (code changed → must be re-reviewed).

5. **After 2 QA iterations still TESTS_FAILED:** show full test-findings.md, ask the user.

---

## Step 7: Create Merge Request

1. Push branch:
   ```bash
   git push -u origin feature/<task-id>
   ```

2. Create GitHub PR using `gh pr create`:
   ```bash
   gh pr create \
     --title "<concise description>" \
     --base main \
     --head feature/<task-id> \
     --body "$(cat <<'EOF'
   ## Summary
   <what was done>

   ## Spec
   <link/path: .agent/<task-id>/spec.md — chosen approach + API contract>

   ## Changes
   <changed files/components>

   ## Test Results
   - Backend: pytest X/Y passed
   - Frontend: vitest X/Y passed

   ## Acceptance Criteria
   <checked list from test-findings.md>
   EOF
   )"
   ```

3. Report to user:
   - PR link
   - Changed files
   - Test results
   - Any unresolved H-items
   - "After PR merge → test deploys automatically via GitHub Actions"
   - "For prod → run workflow manually with environment=prod"

---

## Rules

- **NEVER push directly to main** — always via MR.
- **Spec first:** no developer runs before `spec.md` is `READY` (except `--quick`).
- The architect writes the spec; developers/reviewers/QA never rewrite it (they may append
  Human-Decision outcomes the orchestrator records).
- **Parallel by default:** batch independent agents into a single message (BE‖FE dev,
  BE‖FE‖security review). Only serialise when streams share files or `--serial` is set.
- `.agent/` is in `.gitignore` — files stay local.
- Developer marks findings `FIXED`; only the reviewer marks `VERIFIED`.
- Reviewer/QA never edit source code — they only write findings.
- Max 3 code-review + 2 QA iterations, then escalate to the user.
