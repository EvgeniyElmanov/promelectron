---
name: ship
description: Open a GitHub Pull Request from the current branch using the project template — the standalone version of /implement Step 7, for when the code is already written and committed and you just want to ship the PR. Derives the task-id (and the GitHub Issue, if any) from the branch, pulls Must-haves from the task's spec, builds the PR body, ensures everything is pushed, creates the PR, and moves the GitHub Project card to In Review.
argument-hint: "[issue#|gh-5|branch] (optional — defaults to the current branch)"
disable-model-invocation: true
allowed-tools: Read Write Bash(git *) Bash(gh *) Bash(jq *)
---

# /ship — Open a GitHub Pull Request

Create a GitHub PR from the **current branch** using the project's PR template. This is the
standalone version of **`/implement` Step 7** — for when the code is already written, committed,
and you just want to open the PR (no spec/dev/review/QA pipeline).

It derives the task context from the branch, gathers the PR body from the task's spec (if present),
ensures everything is pushed, creates the PR, and — for tasks that came from a **GitHub Issue** —
moves the card on the **GitHub Project** board to **In Review** (the human-review signal).

The PR title and body are written in **Russian** (matches the team's review style). **No AI
attribution** in the PR body.

## Input

**Optional argument:** `$1` — an issue reference (`5`, `#5`, `gh-5`), or a branch name. If omitted,
use the **current branch** (`git branch --show-current`).

---

## Step 1: Determine context

Record the repo root and current branch:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current)"
```

If `$1` is given as an issue reference, the branch is expected to be `feature/gh-<N>`; if it is a
branch name, check it out first. Otherwise ship the current branch.

Derive the **task id** and **issue number** from the branch name:

- `feature/<task-id>` → `<task-id>` is the part after `feature/`.
- `feature/gh-<N>` → `<task-id>` = `gh-<N>` **and** the GitHub Issue is `#<N>` (the PR will close
  it on merge, and the board card will move to In Review).
- Any other branch shape → treat as a **free-text** task: `<task-id>` is the branch's last path
  segment, there is no issue, and there is no board card.

Never ship from `main`. If `BRANCH` is `main` (or empty / detached HEAD), STOP and ask the user
which branch to ship.

Set the coordination-plane path (gitignored — see the `pipeline-workspace` skill; **never** write
the committed `.agent/` planner):

```bash
AGENT_DIR="$PROJECT_ROOT/.agent/runs/<task-id>"
```

Compute the diff vs `main` so you can describe and sanity-check the PR:

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" log origin/main..HEAD --oneline
git -C "$PROJECT_ROOT" diff origin/main...HEAD --stat
```

If `origin/main..HEAD` is empty there is nothing to ship — tell the user and stop.

---

## Step 2: Ensure everything is pushed

The PR must reflect committed, pushed work.

1. `git -C "$PROJECT_ROOT" status --porcelain` — if there are **uncommitted changes**, STOP and
   tell the user to commit (or stash) them first. `/ship` does not commit code.
2. Check for **unpushed commits**: `git -C "$PROJECT_ROOT" log @{u}..HEAD --oneline 2>/dev/null`
   (or `origin/<branch>..HEAD` if there is no upstream yet). If there are unpushed commits — or no
   upstream at all — **ask the user whether to push**. On yes:
   ```bash
   git -C "$PROJECT_ROOT" push -u origin HEAD
   ```
   On no, stop (cannot open a PR for an unpushed branch).

---

## Step 3: Gather the PR body

Read `$AGENT_DIR/spec.md` **if it exists** and pull its **Must-haves** into the PR body. Read
`$AGENT_DIR/review/test-findings.md` if present for the Test Results / Acceptance Criteria. If
there is no spec (free-text branch shipped directly), derive Summary and Changes from the commit
log and `--stat` diff instead.

**Always** add a **Testing Notes** (Заметки для тестирования) section for the reviewer — main
scenario, edge cases, out-of-scope — even when there is no spec. Infer it from the diff.

---

## Step 4: Create the Pull Request

Match the body shape of `/implement` Step 7 (Summary / Spec / Changes / Test Results / Acceptance
Criteria), plus the always-on Testing Notes. Write **in Russian**. For a **GitHub Issue** task,
include `Closes #<N>` so merging the PR closes the issue.

```bash
gh pr create --base main --head "$BRANCH" \
  --title "<краткое описание задачи>" \
  --body "$(cat <<'EOF'
## Описание
<что сделано — 1-3 предложения>

## Spec
.agent/runs/<task-id>/spec.md — выбранный подход + API-контракт
<!-- опустить эту секцию, если spec.md нет -->

## Изменения
- <ключевые изменённые файлы / компоненты>

## Результаты тестов
- Backend: pytest X/Y · Frontend: vitest X/Y
<!-- из review/test-findings.md, если есть; иначе из прогона разработчика -->

## Критерии приёмки
- [ ] <Must-have / acceptance criterion 1>
- [ ] <Must-have / acceptance criterion 2>
<!-- из Must-haves в spec.md, если есть -->

## Заметки для тестирования
- Основной сценарий: <описание>
- Edge cases: <что может пойти не так>
- Вне скоупа: <что не нужно проверять>

Closes #<N>
<!-- только для задач из GitHub Issue; иначе убрать -->
EOF
)"
```

Capture the printed PR URL for the report.

---

## Step 5: Move the GitHub Project card → In Review

**GitHub Issue tasks only.** AFTER the PR exists, load the **`github-project`** skill and set the
card status `pr_opened → In Review` for issue `#<N>`. This is the human-review signal.

- **Idempotent / never regress:** read the card's current status first; skip if it is already at
  In Review or further along; never push it backwards.
- **Do NOT set Done** — `/ship` does not merge. Only set Done if the user **explicitly** asks.
- If the `project` scope is missing, follow the `github-project` skill: tell the user how to fix it
  and note in the report that the board was not updated. Do not pretend it succeeded.

For **free-text** tasks (no issue) there is no card — skip this step silently.

---

## Step 6: Post open Human-Decision items as PR comments

If `$AGENT_DIR/review/findings.md` exists and has **open** Human-Decision `[H-xxx]` items, post
each one as a PR comment so the reviewer sees the open questions:

```bash
gh pr comment "$BRANCH" --body "[H-xxx] <the open human-decision item>"
```

These are the only comments `/ship` posts. If there is no findings.md or no open H-items, skip.

---

## Step 7: Report (in Russian)

Give the user a tight report:

- **PR:** the URL.
- **Доска:** статус теперь **In Review** (или «доска не обновлена — задача free-text / нет
  карточки», or «не удалось — нет project-скоупа»).
- **H-items:** how many open `[H-xxx]` items were posted as comments (or none).

---

## Rules

- **Never merge.** `/ship` only opens the PR; a human reviews and merges. Don't set Done unless the
  user explicitly asks.
- **Never push to `main`**; never ship from `main`.
- **Never commit code.** If the tree is dirty, stop and ask the user to commit first.
- **Russian PR title + body. No AI attribution** in the PR body.
- **Idempotent board move.** `pr_opened → In Review` only; read current status, never regress.
- **GitHub Issue tasks only** touch the board and use `Closes #<N>`. Free-text branches get a
  plain PR with no card and no `Closes`.
- Coordination files live in the gitignored `.agent/runs/<task-id>/`; **never** write the committed
  `.agent/` planner and never `git add .agent/runs/`.
