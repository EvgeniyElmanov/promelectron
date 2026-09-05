---
name: architect
description: Produce a standalone technical specification via the architect agent — without running the full /implement pipeline. Fetch the task (GitHub Issue or free text) into the coordination plane, invoke the architect agent to write spec.md, drive the clarifications loop with the user, and present the result. Planning only — runs no development, opens no PR, and never moves the GitHub Project board. Hands off to /implement.
argument-hint: "<issue#|gh-5|free text>"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(mkdir *) Task
---

# /architect — Standalone Technical Spec

Produce a technical specification via the **`architect` agent**. Writes
`.agent/runs/<task-id>/spec.md`.

Use this command when you want **just the spec** without running the full `/implement` pipeline —
to discuss an approach, share it with teammates, or do research-heavy planning before committing
to a build. The architect writes the spec; you (orchestrator) only drive the loop and talk to the
user.

> **Planning only.** This command does **NOT** run development, does **NOT** open a PR, and does
> **NOT** move the GitHub Project board. All output lives under `.agent/runs/<task-id>/`
> (gitignored — see the `pipeline-workspace` skill). **Never** write into the committed `docs/`
> planner (`BACKLOG.md`, `DECISIONS.md`, `tasks/` …) — that is a separate human planning system.

## Input: $ARGUMENTS

- **GitHub Issue** (`5`, `#5`, `gh-5`, or an issue URL) — fetch the task, save to
  `.agent/runs/gh-<N>/task.md`, then invoke the architect.
- **Free text** (e.g. `"add rate limiting to payment API"`) — generate a slug, save the
  description to `.agent/runs/<slug>/task.md`, then invoke the architect.
- **No input** — ask the user which task to spec and **wait**.

## Process

### Step 1: Prepare the workspace

Record the repo root: `PROJECT_ROOT="$(git rev-parse --show-toplevel)"`. Derive `<task-id>` and
the coordination dir:

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/research"
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
```

**Reuse first.** If `.agent/runs/<task-id>/task.md` already exists (handed off from `/brainstorm`
or `/implement`), do **NOT** regenerate it — read it and build on it.

**If a GitHub Issue:**
1. Extract the issue number `<N>`; `task-id` = `gh-<N>`.
2. Fetch it: `gh issue view <N> --json number,title,body,comments,url,labels`.
3. Write `.agent/runs/gh-<N>/task.md` in the **GitHub-Issue `task.md` format** from the
   `pipeline-workspace` skill.

**If free text:**
1. Generate `task-id` — a short kebab-case slug (lowercase, hyphens, ~30 chars).
2. Write `.agent/runs/<slug>/task.md` in the **free-text format** with the description.

### Step 2: Invoke the architect agent

Use `subagent_type=architect`. The agent reads context in parallel, brainstorms 2–3 approaches,
and writes the spec per its own template. Prompt:

```
Write a technical specification (Spec-Driven Development) for the task.
AGENT_DIR (coordination, absolute): <AGENT_DIR>
PROJECT_ROOT (code to explore, absolute): <PROJECT_ROOT>
Read AGENT_DIR/task.md. Read AGENT_DIR/research/*.md and AGENT_DIR/brainstorm.md if present and
synthesize into AGENT_DIR/research.md. Explore the codebase (FastAPI backend/, Vue 3 frontend/) to
understand integration points. Produce AGENT_DIR/spec.md per your template.
If a requirement is ambiguous and changes the design, set Status: NEEDS_CLARIFICATION and list the
open questions under "Clarifications Needed" — do NOT guess.
```

### Step 3: Clarification loop

Read `AGENT_DIR/spec.md`.

- **If `Status: NEEDS_CLARIFICATION`** (or the recommended approach is a consequential choice the
  user should own): present the open questions to the user via `AskUserQuestion`, append their
  answers to the `## Clarifications` section of `task.md`, then re-invoke the architect:
  ```
  AGENT_DIR (absolute): <AGENT_DIR>
  The user answered the open questions — see AGENT_DIR/task.md ## Clarifications.
  Update spec.md, convert answered questions into D-numbers, and set Status: READY when nothing
  blocking remains.
  ```
  Repeat until `Status: READY`.
- **If `Status: READY`:** proceed to Step 4.

### Step 4: Present & confirm

Show the user:
- Path to `spec.md`.
- A tight summary — Task Type, chosen approach, **API Contract**, Must-haves, and D-numbers.
- Ask (in Russian): **«Спека готова. Всё ок или нужно что-то поправить?»**

If the user requests changes, re-invoke the architect with the feedback and return to Step 3.

### Step 5: Done

Stop here. This command does **NOT** run development, does **NOT** create a PR, and does **NOT**
move the GitHub Project board. To build it, suggest (in Russian): **«Готово к разработке?
`/implement <task-id>` подхватит спеку и соберёт всё.»**

## Rules

1. **Planning only** — the architect writes the spec; no developer, reviewer, or QA agent runs
   here, no branch/worktree is created, no PR is opened.
2. **Never moves the GitHub Project board** — even for GitHub-Issue tasks. Board movement belongs
   to `/implement` (`start → In Progress`, `PR opened → In Review`).
3. **The architect owns the spec** — you only drive the clarifications loop and append the user's
   answers to `task.md`. Do not write `spec.md` yourself.
4. **Reuse the workspace** — if `.agent/runs/<task-id>/` exists, build on it; don't regenerate.
5. **Coordination plane only** — write under `.agent/runs/<task-id>/` (gitignored); never touch
   the committed `docs/` planner.
