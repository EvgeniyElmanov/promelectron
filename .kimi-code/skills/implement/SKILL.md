---
name: implement
description: >
  Full development cycle skill for Promelectron.
  Use for implementing new features, adding pages, creating API endpoints, building Vue components, adding database models, schemas, services, migrations, or any task requiring code changes.
  Runs an architect phase in plan mode, creates a git worktree, develops backend and/or frontend, performs a code review loop (max 3 iterations), an E2E test phase, and reports results.
  Triggers on: implement, feature, add, create, build, develop, new page, new API, endpoint, component, model, schema, migration, page, view.
type: prompt
whenToUse: When the user asks to implement a new feature, page, API endpoint, component, model, schema, migration, or any multi-step code change that would benefit from architect → developer → reviewer → e2e workflow.
arguments: "<task description> [--quick] [--backend-only] [--frontend-only]"
disableModelInvocation: false
---

# /skill:implement — Full Development Cycle

Implement a new feature from idea to tested code using isolated git worktrees, plan-mode architecture, review loops, and E2E tests.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule. All Russian-language requirements and subagent prompt preambles live there.

Also: write `task.md`, `spec.md`, findings, reports, and `SESSION_LOG.md` entries in Russian when the user is Russian.

---

## Step 1: Parse and Setup

Extract from the user request:
- Task description (everything before flags)
- Flags: `--quick`, `--backend-only`, `--frontend-only`

Generate `<task-id>`: short kebab-case slug, e.g. `add-promo-codes`, `fix-cart-stock`.

Create directories:
```bash
mkdir -p .agent/<task-id>/review
mkdir -p .worktrees
```

Write `.agent/<task-id>/task.md`:
```markdown
# Task: <task-id>

## Description
<full task description>

## Flags
<active flags or "none">

## Date
<YYYY-MM-DD>
```

---

## Step 1b: Context Size Check (Kimi K2.7)

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Context Size Check before launching subagents.

---

## Step 1c: Retry Policy

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Retry Policy when launching subagents.

---

## Step 2: Architect Phase (skip if --quick)

You are the `architect`. Read `.kimi-code/skills/architect/SKILL.md` and follow it strictly.

Launch an architect subagent via `Agent` tool with `subagent_type: plan`. Apply the retry policy from Step 1c:

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are the architect for Promelectron.
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/<task-id>/task.md
2. PROJECT_CONTEXT.md
3. .agent/BACKLOG.md
4. .agent/BLOCKERS.md
5. .agent/SESSION_LOG.md
6. `.kimi-code/skills/architect/SKILL.md`
7. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)

Then:
1. Call EnterPlanMode.
2. Load as much relevant context as possible in **parallel**: read task files, existing code, and external docs/WebSearch results simultaneously.
3. Explore the codebase with Read/Grep/Glob (run multiple reads/searches in parallel) to understand how the feature fits.
4. Use WebSearch/FetchURL if you need external documentation, API docs, or library examples.
5. Ask the user clarifying questions via AskUserQuestion if requirements are unclear.
6. Write a technical specification to the plan file returned by EnterPlanMode. Include:
   - Task Type
   - Analysis
   - Decisions (D-01, D-02, ...)
   - Components Affected (backend/frontend/infra)
   - Technical Design
   - API Changes
   - Must-haves
   - Acceptance Criteria
   - Out of Scope
6. Call ExitPlanMode.

Do NOT write implementation code, tests, or migrations.

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

After the user approves the plan, copy the plan file content to `.agent/<task-id>/spec.md`.

If the user rejects or requests revisions, send the architect back to revise the plan.

---

## Step 3: Developer Worktree

Determine which roles are needed from `Components Affected` in the spec:
- Backend → `backend-dev`
- Frontend → `frontend-dev`
- DevOps → `devops`

Order: backend → frontend → devops (if multiple).

For each role, launch a developer subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are <ROLE> for Promelectron.
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. `.kimi-code/skills/<ROLE>/SKILL.md`
7. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)

Setup:
1. Create an isolated git worktree:
   git worktree add .worktrees/implement-<task-id> -b feature/<task-id>
2. cd .worktrees/implement-<task-id>
3. Work ONLY inside this directory.

Implement strictly per the spec and your role workflow:
- backend-dev: model → schema → service → route handler → tests
- frontend-dev: API service → composable → component → page → route → tests
- devops: Helm/Docker → CI/CD → verify

Rules:
- Business logic belongs in services, NOT route handlers.
- Every new endpoint must have tests.
- Every model change must have an Alembic migration.
- Use trailing slash in FastAPI endpoints.
- Do NOT commit to main. You may commit to feature/<task-id> in the worktree.

Before finishing:
1. Run the role-specific tests (e.g. cd backend && make test-backend; cd frontend && npm test -- --run).
2. Run lint (ruff / npm run lint).
3. Update .agent/SESSION_LOG.md from the worktree.

Report:
- Changed files
- Test results
- Any blockers

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

If both backend and frontend are needed, run backend first, then frontend in the **same** worktree (they share the feature branch).

---

## Step 4: Code Review Loop (max 3 iterations)

### Determine review scope

Based on the spec and flags (`--backend-only`, `--frontend-only`):

- **Backend only or frontend only** → run one reviewer subagent.
- **Mixed (backend + frontend)** → run two reviewer subagents in parallel via `AgentSwarm`.

### Single-component review

Launch one reviewer subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are the code-reviewer for Promelectron.
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)

Then:
1. Read the implementation in .worktrees/implement-<task-id>/ (use Read/Grep/Glob in parallel).
2. Compare against the spec and Decisions (D-01, D-02, ...).
3. Check: logic, security, architecture, business rules, tests, golden path impact.
4. Write findings to .agent/<task-id>/review/findings.md using this format:

# Code Review: <task-id>
- **Status:** FIXES_NEEDED | APPROVED
- **Iteration:** <N>

## Findings
### [F001] ❌ CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Problem:** ...
- **Fix:** ...
- **Status:** OPEN

## Human Decisions (if any)
### [H001] ...

Do NOT edit source code. Only write findings.

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

### Mixed review (backend + frontend in parallel)

Launch reviewer subagents via `AgentSwarm` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are the code-reviewer for Promelectron (focus: {{item}}).
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. `.kimi-code/skills/code-reviewer/SKILL.md`
4. [Rule: Security](.kimi-code/rules/security.md)

Then:
1. Read only {{item}} implementation files in .worktrees/implement-<task-id>/ (use Read/Grep/Glob in parallel).
2. Compare against the spec and Decisions (D-01, D-02, ...).
3. Check: logic, security, architecture, business rules, tests, golden path impact for {{item}}.
4. Write findings to .agent/<task-id>/review/findings-{{item}}.md using this format:

# Code Review: <task-id> ({{item}})
- **Status:** FIXES_NEEDED | APPROVED
- **Iteration:** <N>
- **Scope:** {{item}}

## Findings
### [F001] ❌ CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Problem:** ...
- **Fix:** ...
- **Status:** OPEN

## Human Decisions (if any)
### [H001] ...

Do NOT edit source code. Only write findings.

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

items: `["backend", "frontend"]`

**After `AgentSwarm` returns:**
1. Read `.agent/<task-id>/review/findings-backend.md` and `.agent/<task-id>/review/findings-frontend.md`.
2. Merge them into `.agent/<task-id>/review/findings.md`:
   - Overall **Status** is `FIXES_NEEDED` if any sub-report is `FIXES_NEEDED`; otherwise `APPROVED`.
   - Preserve **Iteration** number.
   - Combine findings lists; renumber if needed so IDs are unique across backend and frontend.
   - Preserve Human Decisions from both reports.
3. Delete the temporary `findings-backend.md` and `findings-frontend.md` or keep them for debugging.

### Review loop continuation

1. Read `.agent/<task-id>/review/findings.md`.
2. If `APPROVED` → go to Step 5.
3. If `FIXES_NEEDED`:
   - Show the user a summary of findings.
   - For H-items, wait for user decision.
   - Launch the developer subagent again to fix OPEN findings and mark them FIXED.
   - **Before repeating review, re-run the relevant tests** (backend: `make test-backend`; frontend: `npm run test:unit -- --run`). If tests fail, fix them first.
   - Repeat review.
4. After 3 iterations still `FIXES_NEEDED` → stop and ask the user how to proceed.

---

## Step 5: QA / Test Pyramid

After code review passes, launch a `qa` subagent via `Agent` tool with `subagent_type: coder`. Apply the retry policy from Step 1c:

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are the qa engineer for Promelectron.
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.
Read:
1. .agent/<task-id>/task.md
2. .agent/<task-id>/spec.md
3. .agent/<task-id>/review/findings.md
4. PROJECT_CONTEXT.md
5. .agent/BACKLOG.md
6. .agent/BLOCKERS.md
7. `.kimi-code/skills/qa/SKILL.md`
8. [Rule: Golden Path](.kimi-code/rules/golden-path.md)

Then:
1. Run backend tests: cd backend && make test-backend
2. Run frontend unit tests: cd frontend && npm run test:unit -- --run
3. If the feature touches UI or user flows, run E2E tests. You may delegate the E2E-specific work to an e2e-tester subagent; if you do, pass the feature scope and spec explicitly.
4. Verify each Acceptance Criterion from spec.md.
5. Write results to .agent/<task-id>/review/test-findings.md.

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

The `qa` subagent may launch an `e2e-tester` subagent for the browser-automation part if needed.

CI already runs E2E on the test environment (`promelectron-test`) after deploy.

---

## Step 6: Final Report

After all phases:

1. Run `python scripts/implement-pipeline.py check-context <task-id>` to capture final estimated tokens.
2. Read `.agent/SESSION_LOG.md` and append a summary including estimated tokens and iteration count.
3. Report to the user:
   - Task ID
   - Worktree path: `.worktrees/implement-<task-id>`
   - Feature branch: `feature/<task-id>`
   - Changed files
   - Test results (backend, frontend, e2e)
   - Review status
   - Estimated tokens and iteration count
   - Open findings or H-items (if any)
3. Push the feature branch to origin (allowed by permission rules):
   ```bash
   git push origin feature/<task-id>
   ```
4. Ask: **"Merge feature/<task-id> into main and push?"** (do NOT merge or push main without explicit approval).

---

## Rules

- NEVER push directly to `main`.
- NEVER delete the worktree until the user approves merge or explicitly asks to clean up.
- Developer marks findings FIXED; reviewer verifies and marks VERIFIED.
- Max 3 review iterations, then escalate to user.
- Update `.agent/SESSION_LOG.md` after every significant phase.
