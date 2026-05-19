---
name: fix-test
description: Diagnose and fix a failing test. Identifies root cause (bug in implementation vs wrong test), applies the fix, and verifies the full suite still passes. Delegates to qa agent.
argument-hint: "<test name or file path>"
disable-model-invocation: false
context: fork
agent: qa
---

# Fix Failing Test: $ARGUMENTS

Diagnose and fix: **$ARGUMENTS**

## Steps

1. Run the failing test and capture full output:
   - Backend: `cd backend && uv run pytest "$ARGUMENTS" -x -v 2>&1`
   - Frontend: `cd frontend && npm test -- "$ARGUMENTS" --reporter=verbose`
2. Read the test file to understand what is being tested
3. Read the implementation being tested
4. Identify root cause — choose one:
   - **Bug in implementation** → fix the code, not the test
   - **Test is wrong** → fix the test expectation (document why)
   - **Missing fixture/setup** → add proper setup
   - **Flaky timing** → add proper async handling or mocking
5. Apply the fix
6. Run the specific test to confirm it passes
7. Run the full suite to check for regressions:
   - Backend: `cd backend && uv run pytest -x`
   - Frontend: `cd frontend && npm test`

## Rules
- Never skip or xfail a test without a documented reason
- Never mock the database layer in backend tests — use real test DB
- External API calls in tests must use `respx` mocking
