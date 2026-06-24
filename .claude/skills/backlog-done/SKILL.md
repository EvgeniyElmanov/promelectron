---
name: backlog-done
description: Close a backlog item (a GitHub Issue) — completed (default) or not-planned (drop). Closes the issue via gh, optionally moves the Project card to Done when completed, and optionally posts a closing comment when the user gives a reason. Closing is a status flip; nothing is deleted.
argument-hint: "<issue#|#5|gh-5> [drop] [reason…]"
disable-model-invocation: true
allowed-tools: Read Write Bash(gh *) Bash(jq *) Bash(git *) Bash(mkdir *)
---

# /backlog-done — Close a backlog item

The backlog **is GitHub** — open [GitHub Issues](https://github.com/AutonomaCo/promelectron/issues)
on the **GitHub Project (v2)** board. This command closes one issue. Closing is a **status flip**,
not a deletion — the issue stays as history.

## Input: $ARGUMENTS

- `<issue#>` — the issue reference: `5`, `#5`, or `gh-5`. Required. Strip the prefix → number `<N>`.
  If empty/ambiguous, list open issues and ask which one.
- optional `drop` token — close as **not planned** (consciously rejected) instead of **completed**.
- any remaining free text — an optional closing **reason** to post as a comment.

## Pipeline

### Step 1: Resolve

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
gh issue view <N> --json number,title,state,url
```

If the issue doesn't exist, tell the user (in Russian) and stop. If it's already closed, say so and
confirm before re-running.

### Step 2: Close the issue

Default reason is **completed**; `drop` means **not planned**.

```bash
# completed (default):
gh issue close <N> --reason completed
# dropped (when the `drop` token was passed):
gh issue close <N> --reason "not planned"
```

### Step 3: Closing comment (optional)

If the user supplied a reason in the arguments, post it before/with the close so the record is clear:

```bash
gh issue comment <N> --body "<the reason — what shipped / why dropped>"
```

Skip if no reason was given.

### Step 4: Move the Project card (completed only)

When closing as **completed**, load the `github-project` skill and set status `merged → Done`
(idempotent — read current status first, never regress). For a **drop** there's no "Done"
milestone; closing the issue is enough (the board's automation typically clears closed cards).

If the `project` scope is missing (`missing required scopes`), STOP and tell the user to run, in
their own shell (it is interactive — you cannot do it):

```
gh auth refresh -s project
```

Note that the board was not updated rather than pretending it succeeded.

### Step 5: Report (in Russian)

`✓ #<N> «<title>» → done` (completed) or `✓ #<N> «<title>» → dropped` (not planned), and the board
status (now `Done`, or "карточка не двигалась" / not applicable for a drop). Mention
`gh issue list` to see what's left open.

## Rules

1. **GitHub is the backlog.** Close via `gh issue close`; never edit local backlog files.
2. **Don't delete** — closing is a status flip; the issue stays as history.
3. **`completed` vs `dropped`** — default `--reason completed`; `drop` → `--reason "not planned"`.
   Only `completed` moves the board to Done.
4. **Fail loud on missing scope** — `project` scope is needed to move cards; tell the user to
   `gh auth refresh -s project` and note the board is out of sync.
5. **Never touch the committed `.agent/` planner.**
