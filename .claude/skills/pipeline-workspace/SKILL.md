---
name: pipeline-workspace
description: Convention for the per-task pipeline workspace — the gitignored .agent/runs/<task-id>/ coordination plane (task.md, research, spec.md, review/findings.md) and the .worktrees/<task-id>/ code checkout shared between the architect, developers, reviewers, and QA during /implement, /brainstorm, /architect, /qa.
when_to_use: Load whenever a pipeline command or sub-agent needs to know where task context, spec, and review findings live, or how the worktree relates to the coordination plane.
user-invocable: false
---

# Pipeline workspace convention

Each pipeline task gets **two** locations. Keep them straight — they serve different purposes and
have different lifetimes.

| | Path | Lifetime | Git | Holds |
|-|------|----------|-----|-------|
| **Coordination plane** | `.agent/runs/<task-id>/` | durable across worktree removal | **gitignored** | task.md, research/, spec.md, questions.md, review/findings.md, tests/ |
| **Code checkout** | `.worktrees/<task-id>/` | ephemeral, removed after merge | gitignored | the actual code changes on `feature/<task-id>` |

> ### ⚠️ Do NOT confuse `.agent/runs/` with the committed `.agent/` planning dir
> This project's **`.agent/`** root is a **committed** human planning system (`BACKLOG.md`,
> `BLOCKERS.md`, `DECISIONS.md`, `METRICS.md`, `SESSION_LOG.md`, `tasks/`) read at session start
> per the `agent-context` rule. The pipeline's transient per-task files live **only** under
> `.agent/runs/` (gitignored via `/.agent/runs/`). Never write pipeline scratch into the
> committed planning files, and never `git add .agent/runs/`.

## Coordination plane vs. worktree

`/implement` isolates each task in its **own git worktree** so parallel runs never collide.
Sub-agents receive **both** as absolute paths and must target them explicitly (a sub-agent's `cd`
does not persist between tool calls):

- `AGENT_DIR` = `<repo-root>/.agent/runs/<task-id>` — coordination files. Durable; survives
  worktree removal (which is why it is NOT inside the worktree).
- `WORKTREE` = `<repo-root>/.worktrees/<task-id>` — code lives here. Use `git -C <WORKTREE> …`,
  `make -C <WORKTREE> …`, `uv --directory <WORKTREE> …`; Read/Edit/Write files under `<WORKTREE>`.

Record the repo root once: `PROJECT_ROOT="$(git rev-parse --show-toplevel)"`.

## Directory structure

```
.agent/runs/                       # gitignored coordination plane (NOT the committed planner)
  add-product-filters/             # one dir per task — slug or gh-<issue#>
    task.md                        # the task (from a GitHub Issue or free text)
    research/                      # parallel research partials (one file per axis)
      libraries.md  best-practices.md  codebase.md
    research.md                    # architect's synthesized research
    brainstorm.md                  # optional study brief from /brainstorm
    spec.md                        # architect's technical spec (source of truth)
    questions.md                   # open questions to the user (interactive loop)
    review/
      dim-*.md                     # per-dimension review partials (transient)
      findings.md                  # merged reviewer findings (F-/H-numbers)
      test-findings.md             # QA results
    tests/                         # /qa artifacts (cases.md, results.md)
.worktrees/
  add-product-filters/             # branch feature/add-product-filters
```

## Task id

- **GitHub Issue task:** `<task-id>` = `gh-<issue#>` (e.g. `gh-5`). Branch `feature/gh-5`.
  The task is anchored to the issue and its GitHub Project card moves status (see the
  `github-project` skill).
- **Free-text task:** `<task-id>` = a short kebab-case slug from the description
  (e.g. `fix-cart-stock-check`). No issue, no board card.

A command that is handed an existing `<task-id>` (e.g. `/implement gh-5` after `/brainstorm gh-5`)
**reuses** `.agent/runs/<task-id>/` instead of regenerating it.

## File formats

### task.md (GitHub Issue)

```markdown
# Task: gh-5
- **Issue:** https://github.com/AutonomaCo/promelectron/issues/5
- **Title:** Кнопка «Отменить заказ» для пользователя
- **Project status (at fetch):** Todo
- **Source:** github-issue

## Description
[Full issue body]

## Comments
[Relevant issue comments, if any]

## Linked Issues / PRs
[Related, if any]

## Clarifications
[Appended as the user answers — newest at bottom]
```

### task.md (free text)

```markdown
# Task: fix-cart-stock-check
- **Source:** manual
- **Title:** Fix cart stock check

## Description
[Free-text description]

## Clarifications
[Appended as the user answers]
```

### spec.md

Written by the `architect` agent. Source of truth for developers, reviewers, and QA. See the
`architect` agent definition for the full template (Status, Decisions/D-numbers, API Contract,
Must-haves, Acceptance Criteria, Parallelization Plan).

### review/findings.md

Reviewer findings. `F-` numbers = agent-fixable, `H-` numbers = human decisions. Document
`Status:` is `FIXES_NEEDED` or `APPROVED`. Developer marks an item `FIXED`; only the reviewer
marks `VERIFIED`. Reviewers/QA never edit source — they only write findings.

## How agents use the workspace

| Agent | Reads | Writes |
|-------|-------|--------|
| Research fan-out | task.md, code in WORKTREE | research/`<axis>`.md |
| architect | task.md, research/*.md | research.md, spec.md, questions.md |
| backend-dev / frontend-dev | task.md, spec.md, review/findings.md | code in WORKTREE, findings.md (FIXED status) |
| code-reviewer / security-reviewer | task.md, spec.md, diff in WORKTREE | review/dim-*.md → findings.md |
| qa | task.md, spec.md, code in WORKTREE | review/test-findings.md, tests/* |
| Orchestrator (/implement) | review/dim-*.md | findings.md (merged), GitHub Project status |

## Cleanup

The worktree is **kept** after the PR is created so the user can address PR comments in it. Remove
once merged: `git -C "$PROJECT_ROOT" worktree remove .worktrees/<task-id>`. The
`.agent/runs/<task-id>/` dir persists as reference and can be deleted manually anytime.
