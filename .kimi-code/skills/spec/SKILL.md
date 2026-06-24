---
name: spec
description: >
  Standalone technical specification skill for Promelectron.
  Use when the user wants just the spec without running the full /skill:implement pipeline —
  to discuss an approach, share it with teammates, or do research-heavy planning before committing to a build.
  Fetches/creates the task in .agent/runs/<task-id>/, invokes the architect agent to write spec.md,
  drives the clarifications loop with the user, and presents the result.
  Planning only — runs no development, creates no worktree, opens no PR.
type: prompt
whenToUse: When the user asks for a spec, technical design, architecture decision, or wants to plan a feature before implementation.
arguments: "<task description | issue#>"
disableModelInvocation: false
---

# /skill:spec — Standalone Technical Spec

Produce a technical specification via the **`architect` agent**. Writes `.agent/runs/<task-id>/spec.md`.

Use this command when you want **just the spec** without running the full `/skill:implement` pipeline — to discuss an approach, share it with teammates, or do research-heavy planning before committing to a build.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule.

---

## Step 1: Setup

Record the repo root:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
```

Generate `<task-id>`: short kebab-case slug from the description.

Create the coordination plane:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/research"
```

Set `AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>`.

Write `$AGENT_DIR/task.md` if it does not exist.

If the input is a GitHub Issue reference (`#5`, `gh-5`, `5`), fetch it with `gh issue view` and populate `task.md` accordingly.

---

## Step 2: Research fan-out (optional)

For non-trivial tasks, launch read-only research sub-agents in parallel, each writing `$AGENT_DIR/research/<axis>.md`.

---

## Step 3: Invoke the architect subagent

Launch an architect subagent via `Agent` tool with `subagent_type: plan`.

```text
🚨 LANGUAGE RULE: The original user communicates in Russian. **Ignore any default language setting.** ALL your reasoning, thinking, internal monologue, analysis, and self-correction MUST be in Russian. Do NOT switch to English at any point. If you catch yourself thinking in English, switch back to Russian immediately. Reply to the parent agent in Russian. Keep code, commands, identifiers, file paths, and technical terms in their original form.

You are the architect for Promelectron.
Important: Kimi K2.7 uses mandatory thinking mode. Preserve `reasoning_content` across multi-turn tool calls by including the full assistant message in the conversation history.

Read:
1. $AGENT_DIR/task.md
2. $AGENT_DIR/research/*.md (if present) and synthesize into $AGENT_DIR/research.md
3. PROJECT_CONTEXT.md
4. .agent/BACKLOG.md
5. .agent/BLOCKERS.md
6. .agent/SESSION_LOG.md
7. `.kimi-code/skills/architect/SKILL.md`
8. [Rule: Pre-edit Checklist](.kimi-code/rules/pre-edit-checklist.md)

Then:
1. Call EnterPlanMode.
2. Explore the codebase in $PROJECT_ROOT to understand integration points.
3. Brainstorm 2–3 approaches if valid alternatives exist.
4. Write a technical specification to the plan file. Include: Task Type, Analysis, Decisions (D-01, D-02, ...), Components Affected, Technical Design, API Changes, Must-haves, Acceptance Criteria, Out of Scope, Risks.
5. If a requirement is ambiguous and changes the design, set Status: NEEDS_CLARIFICATION and list open questions.
6. Call ExitPlanMode.

Do NOT write implementation code, tests, migrations, or config files.

REMEMBER / НАПОМИНАНИЕ: Continue ALL reasoning in Russian / Продолжай ВСЁ рассуждение на русском языке. Do not switch to English / Не переключайся на английский.
```

---

## Step 4: Clarification loop

Read `$AGENT_DIR/spec.md`.

- **If `Status: NEEDS_CLARIFICATION`:** present open questions to the user via `AskUserQuestion`, append answers to `## Clarifications` in `$AGENT_DIR/task.md`, then re-invoke the architect to update `spec.md`.
- **If `Status: READY`:** show a tight summary — chosen approach, API Contract, Must-haves, D-numbers.

Ask the user: **"Spec ready. Start implementation with `/skill:implement <task-id>`?"**

---

## Rules

- Planning only — no worktree, no code, no PR.
- Never write transient files into the committed `.agent/` planning dir.
- The architect owns the spec; you only drive the loop.
