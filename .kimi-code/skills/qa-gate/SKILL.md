---
name: qa-gate
description: >
  Standalone QA gate skill for Promelectron.
  Use to re-run the QA stage for a task that was already specced and built,
  without re-running the full /skill:implement pipeline.
  Locates the task's coordination plane (.agent/runs/<task-id>/) and worktree (.worktrees/<task-id>/),
  runs backend pytest + frontend vitest + Playwright E2E when UI/API changed,
  verifies Acceptance Criteria from spec.md, and writes review/test-findings.md.
type: prompt
whenToUse: When the user asks to QA a task, run tests for a task, verify a feature, or re-check after fixes.
arguments: "<task-id|slug> [--e2e]"
disableModelInvocation: false
---

# /skill:qa-gate — Standalone QA Stage

Run the **QA gate** for a single task and write its results to `.agent/runs/<task-id>/review/test-findings.md`.

Use this when the code is already written and you want to re-run tests / verify acceptance criteria without invoking the full `/skill:implement` pipeline.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule.

---

## Step 1: Locate the workspace

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
WORKTREE="$PROJECT_ROOT/.worktrees/<task-id>"
```

- If `$AGENT_DIR` is missing — stop and tell the user to run `/skill:spec <task-id>` or `/skill:implement <task-id>` first.
- If `$WORKTREE` is missing — stop and tell the user the worktree was removed; re-create it with `/skill:implement <task-id>`.
- If `$AGENT_DIR/spec.md` is missing — warn that there is no spec; the QA agent still runs the test suites.

---

## Step 2: Invoke the qa subagent

Launch a `qa` subagent via `Agent` tool with `subagent_type: coder`.

```text
ЯЗЫК / LANGUAGE: Пользователь общается на русском. Отвечай родительскому агенту и пиши все артефакты (spec, findings, отчёты, SESSION_LOG) на русском. Стремись рассуждать на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

You are the qa engineer for Promelectron.
Important: Kimi K2.7-Code uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/spec.md (if present)
3. $AGENT_DIR/review/findings.md (if present)
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](.kimi-code/rules/golden-path.md)

Then:
1. Run backend tests in $WORKTREE: make -C "$WORKTREE" test-backend
2. Run frontend unit tests in $WORKTREE: make -C "$WORKTREE" test-frontend
3. If the feature touches UI or user flows (or --e2e was passed), run E2E tests. You may delegate the E2E-specific work to an e2e-tester subagent.
4. Verify each Acceptance Criterion from $AGENT_DIR/spec.md.
5. Write results to $AGENT_DIR/review/test-findings.md.

НАПОМИНАНИЕ: ответы и артефакты — на русском; технические токены (код, пути, команды) — в оригинале.
```

---

## Step 3: Report

Read `$AGENT_DIR/review/test-findings.md` and report to the user:
- Status: `TESTS_PASSED` or `TESTS_FAILED`
- Backend / frontend / E2E counts
- Open F-findings and H-findings
- Path to the report file

If `TESTS_FAILED`, suggest invoking `/skill:implement <task-id>` or the relevant developer role to fix and re-run `/skill:qa-gate <task-id>`.

---

## Rules

- The QA agent never edits source code — only writes findings.
- Do not move the GitHub Project board.
- Keep all reads/writes under `.agent/runs/<task-id>/` and `.worktrees/<task-id>/`.
