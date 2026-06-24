---
name: backlog-pick
description: Take a GitHub Issue from the backlog (GitHub Issues + the GitHub Project board) into work. Fetches the issue, creates the per-task coordination workspace .agent/runs/gh-<N>/ and writes task.md in the GitHub-Issue format the pipeline consumes, optionally moves the Project card to In Progress, then hands off to /brainstorm or /implement.
argument-hint: "<issue#|#5|gh-5>"
disable-model-invocation: true
allowed-tools: Read Write Bash(gh *) Bash(jq *) Bash(git *) Bash(mkdir *)
---

# /backlog-pick — Take a GitHub Issue into work

The backlog **is GitHub** — open [GitHub Issues](https://github.com/AutonomaCo/promelectron/issues)
on the **GitHub Project (v2)** board. This command promotes one issue into a regular pipeline task
workspace (`.agent/runs/gh-<N>/task.md`, exactly the shape `/brainstorm`, `/architect`, and
`/implement` already consume — see the `pipeline-workspace` skill) and hands off to one of them.
**Picking ≠ starting** — the issue stays open and the board moves only if the user is starting now.

## Input: $ARGUMENTS

A single issue reference: `5`, `#5`, or `gh-5`. Strip the `#`/`gh-` prefix to get the number `<N>`;
`task-id` = `gh-<N>`. If empty or ambiguous, list open issues
(`gh issue list --state open --json number,title --jq '.[] | "#\(.number) \(.title)"'`) and ask
which one.

## Pipeline

### Step 1: Fetch the issue

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
gh issue view <N> --json number,title,body,comments,url
```

If the issue does not exist or is already closed, tell the user (in Russian) and stop / confirm
before proceeding. Note its `state` so you don't silently pick a closed item.

### Step 2: Create the coordination workspace

```bash
mkdir -p "$PROJECT_ROOT/.agent/runs/gh-<N>/review"
```

This is the **gitignored coordination plane** (`.agent/runs/…`) — NOT the committed `.agent/`
planner. Never `git add` it.

### Step 3: Write task.md (GitHub-Issue format)

Write `$PROJECT_ROOT/.agent/runs/gh-<N>/task.md` in the exact GitHub-Issue format from the
`pipeline-workspace` skill so downstream commands reuse it verbatim:

```markdown
# Task: gh-<N>
- **Issue:** <url>
- **Title:** <title>
- **Project status (at fetch):** <current board column, or "—" if unknown / not on board>
- **Source:** github-issue

## Description
<full issue body>

## Comments
<relevant issue comments, if any>

## Linked Issues / PRs
<related, if any>

## Clarifications
<empty — appended later as the user answers>
```

Do **not** close the issue — it stays open as provenance and is the anchor for the board card.

### Step 4: Move the Project card (ask first — optional)

Picking is not necessarily starting. Ask the user (in Russian) whether to start now:

> **Двигаем карточку `gh-<N>` в «In Progress» сейчас? (берём в работу прямо сейчас или просто
> готовим задел)**

If **yes**: load the `github-project` skill and set status `start → In Progress` (idempotent —
read current status first, never regress). If the `project` scope is missing
(`missing required scopes`), STOP and tell the user to run, in their own shell (it is interactive —
you cannot do it):

```
gh auth refresh -s project
```

Note that the board was not updated rather than pretending it succeeded.
If **no**: leave the card where it is.

### Step 5: Hand off (interactive)

Ask the user (in Russian) how to proceed with `AskUserQuestion`:

> **Задача `gh-<N>` «<title>» готова в `.agent/runs/gh-<N>/`. Что дальше?**
> - **Брейншторм** — изучить/сравнить варианты: `/brainstorm gh-<N>`
> - **Реализация** — сразу в разработку: `/implement gh-<N>`
> - **Ничего пока** — просто оставить задел в `.agent/runs/gh-<N>/`

Both `/brainstorm` and `/implement` detect the existing `.agent/runs/gh-<N>/task.md` and reuse it
instead of regenerating, so the handoff is a single command. **Print the exact next command** for
the chosen option — do **not** auto-run another slash command.

### Step 6: Report (in Russian)

`✓ #<N> «<title>» → .agent/runs/gh-<N>/task.md` plus the board status (now `In Progress`, or
"карточка не двигалась") and the suggested next command.

## Rules

1. **GitHub is the backlog.** No local backlog files — fetch via `gh`, write to the gitignored
   `.agent/runs/gh-<N>/` coordination plane only.
2. **Keep provenance** — never close the issue; picking just prepares the workspace.
3. **Picking ≠ starting** — move the board only when the user confirms they're starting now.
4. **Fail loud on missing scope** — `project` scope is needed to move cards; tell the user to
   `gh auth refresh -s project` and note the board is out of sync.
5. **Don't chain slash commands** — surface the next command for the user to run.
6. **Never touch the committed `.agent/` planner.**
