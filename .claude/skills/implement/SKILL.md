---
name: implement
description: Full development cycle for any feature or bug fix. Runs architect phase, then developer → code-review loop → QA loop → Merge Request creation.
argument-hint: "<task description> [--quick] [--backend-only] [--frontend-only]"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(mkdir *) Bash(ls *)
---

# /implement — Full Development Cycle

Flags:
- `--quick` — skip architect phase (use for trivial tasks)
- `--backend-only` — only invoke backend-dev
- `--frontend-only` — only invoke frontend-dev

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
```

---

## Step 2: Architect Phase (skip if --quick)

**You are the architect.** Analyse the task in context of the project:

1. Read relevant existing code to understand current structure
2. Ask the user clarifying questions if anything is ambiguous — wait for answers
3. Propose approach with trade-offs if multiple options exist — wait for user choice
4. Write `.agent/<task-id>/spec.md`:

```markdown
# Technical Specification: <task-id>

## Task Type
Feature | Bug Fix | Refactoring

## Analysis
[How the task fits into existing architecture]

## Decisions
- **D-01:** [Decision with rationale — developer must follow exactly]

## Components Affected
- Backend: [files/modules] | Not affected
- Frontend: [files/modules] | Not affected

## Technical Design
[What to create/modify and how]

## Must-haves
- [ ] Behaviour 1
- [ ] Behaviour 2

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Out of Scope
- [What this task does NOT include]
```

Tell user: "Spec ready. Shall I start implementation?"
**Wait for user confirmation before continuing.**

---

## Step 3: Git Branch

```bash
git fetch origin
git checkout -b feature/<task-id> origin/main
```

---

## Step 4: Implementation

Based on Components Affected in spec.md, invoke the appropriate developer subagent(s):

**If backend affected (and not --frontend-only):**
Invoke `backend-dev`:
```
Implement the task.
Task directory: .agent/<task-id>/
Read task.md and spec.md before starting.
```

**If frontend affected (and not --backend-only):**
Invoke `frontend-dev`:
```
Implement the task.
Task directory: .agent/<task-id>/
Read task.md and spec.md before starting.
```

---

## Step 5: Code Review Loop (max 3 iterations)

### Each iteration:

1. Invoke `code-reviewer`:
   ```
   Review the code changes.
   Task directory: .agent/<task-id>/
   Read spec.md. Write results to review/findings.md.
   ```

2. Read `.agent/<task-id>/review/findings.md`

3. **If `APPROVED`** → go to Step 6

4. **If `FIXES_NEEDED`:**
   - Show user: findings summary + any `[H-xxx]` Human Decision items
   - For H-items: wait for user decision, update spec.md with decision
   - Invoke developer(s) to fix:
     ```
     Fix findings from review/findings.md.
     Task directory: .agent/<task-id>/
     Fix all OPEN items and mark them FIXED with Developer note.
     ```
   - Repeat from iteration start

5. **After iteration 3, still FIXES_NEEDED:** Show user remaining open findings. Ask how to proceed. Do not continue automatically.

---

## Step 6: QA Loop (max 2 iterations)

1. Invoke `qa`:
   ```
   Run tests and verify acceptance criteria.
   Task directory: .agent/<task-id>/
   Read spec.md. Write results to review/test-findings.md.
   ```

2. Read `.agent/<task-id>/review/test-findings.md`

3. **If `TESTS_PASSED`** → go to Step 7

4. **If `TESTS_FAILED`:**
   - Show user test failures summary
   - Invoke developer(s) to fix:
     ```
     Fix test failures from review/test-findings.md.
     Task directory: .agent/<task-id>/
     Fix all OPEN items.
     ```
   - Return to **Step 5** (code review) — code changed so it must be re-reviewed

5. **After 2 QA iterations still TESTS_FAILED:** Show full test-findings.md and ask user how to proceed.

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

- **NEVER push directly to main** — always via MR
- `.agent/` is in `.gitignore` — files stay local
- Developer never marks findings `VERIFIED` — only reviewer does
- Reviewer never edits source code — only writes findings.md
- QA never edits source code — only writes test-findings.md
- Max 3 code-review + 2 QA iterations, then escalate to user
