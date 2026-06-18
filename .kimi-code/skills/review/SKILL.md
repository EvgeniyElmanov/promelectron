---
name: review
description: >
  Code review skill for Promelectron. Performs security audit, quality checks, and test coverage analysis on current changes
  or specified files. Writes findings to .agent/<task-id>/review/findings.md.
  Can run in full mode (security + quality + tests), security-only mode, or quick mode.
type: prompt
whenToUse: When the user asks for a code review, audit, findings, quality check, or asks "check this code".
arguments: "[--security-only] [--quick] [<files>]"
disableModelInvocation: false
---

# /review — Code Review

Review current changes. Do NOT edit code — only write findings.

---

## Step 1: Get Diff

```bash
git diff
```

If files are specified:
```bash
git diff -- <files>
```

---

## Step 2: Security Checks (skip if --quick)

- [ ] Auth guards on all new non-public endpoints
- [ ] Admin endpoints check admin role
- [ ] Users can only access their own data
- [ ] No raw SQL with string formatting
- [ ] All inputs validated via Pydantic
- [ ] No PII or tokens in logs/responses
- [ ] Prices from DB, not client
- [ ] Stock checked atomically (`SELECT FOR UPDATE`)
- [ ] Filename sanitized (`os.path.basename` + `os.path.realpath`)

---

## Step 3: Quality Checks

**Backend:**
- [ ] Business logic in `services/`, not route handlers
- [ ] Type hints on public methods
- [ ] Error handling (no bare 500s)
- [ ] No N+1 queries (`selectinload` where needed)
- [ ] Async/await for DB operations

**Frontend:**
- [ ] Composition API (`<script setup>`)
- [ ] `data-testid` for E2E selectors
- [ ] Loading/error/empty states handled
- [ ] No `console.log` / `debugger`

**General:**
- [ ] Follows project conventions
- [ ] No hardcoded secrets or URLs
- [ ] Comments explain "why", not "what"

---

## Step 4: Tests Check

- [ ] New behavior has tests
- [ ] Happy path + error cases covered
- [ ] Existing tests not broken
- [ ] E2E selectors added when UI changed

---

## Step 5: Write Findings

Write to `.agent/<task-id>/review/findings.md`:

```markdown
# Code Review: <task-id or date>
- **Status:** APPROVED | FIXES_NEEDED
- **Scope:** <files reviewed>
- **Reviewer:** code-reviewer

## Findings
### [F001] ❌ CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Problem:** ...
- **Fix:** ...
- **Status:** OPEN

## Human Decisions
### [H001] ...
```

---

## Step 6: Report

Report to the user:
- Status
- Number of issues by severity
- File path with findings

---

## Rules

- NEVER edit source code.
- NEVER mark findings VERIFIED — only the reviewer does after re-checking.
- Classify: CRITICAL | HIGH | MEDIUM | LOW.
- Security issues default to HIGH or CRITICAL.
