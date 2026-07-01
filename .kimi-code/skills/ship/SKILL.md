---
name: ship
description: >
  Open a GitHub Pull Request from the current feature branch.
  For when the code is already written and committed and you just want to ship the PR.
  Derives the task-id from the branch, pulls Must-haves from the task's spec,
  builds the PR body, pushes if needed, creates the PR, and posts open [H-xxx] items as PR comments.
type: prompt
whenToUse: When the user asks to open a PR, ship a feature, create a pull request, or when /skill:implement would normally create a PR.
arguments: "[task-id|branch] (optional — defaults to the current branch)"
disableModelInvocation: false
---

# /skill:ship — Open a GitHub Pull Request

Create a GitHub PR from the **current feature branch** using the project's PR template. This is the standalone version of `/skill:implement` Step 8 — for when the code is already written, committed, and you just want to open the PR.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule. PR title and body are written in Russian when the user is Russian.

---

## Step 1: Determine context

Record the repo root and current branch:

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
BRANCH="$(git -C "$PROJECT_ROOT" branch --show-current)"
```

If a task-id or branch was provided as an argument:
- If it starts with `feature/` → use it as the branch and derive `task-id` from the suffix.
- Otherwise treat it as `task-id`; the branch is expected to be `feature/<task-id>`.

If the current branch is `main` (or detached HEAD), stop and ask the user which branch to ship.

Derive:
- `feature/<task-id>` → `task-id`
- Branch suffix after the last `/` if no `feature/` prefix.

Set `AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>`.

Fetch the diff vs `origin/main`:

```bash
git -C "$PROJECT_ROOT" fetch origin
git -C "$PROJECT_ROOT" log origin/main..HEAD --oneline
git -C "$PROJECT_ROOT" diff origin/main...HEAD --stat
```

If there are no commits to ship, tell the user and stop.

---

## Step 2: Ensure everything is pushed

1. `git -C "$PROJECT_ROOT" status --porcelain` — if there are uncommitted changes, stop and tell the user to commit or stash first. `/skill:ship` does not commit code.
2. Check for unpushed commits: `git -C "$PROJECT_ROOT" log @{u}..HEAD --oneline 2>/dev/null` (or `origin/<branch>..HEAD` if no upstream). If there are unpushed commits — or no upstream — ask the user whether to push. On yes:
   ```bash
   git -C "$PROJECT_ROOT" push -u origin HEAD
   ```

---

## Step 3: Gather the PR body

Read `$AGENT_DIR/spec.md` if it exists and pull its **Must-haves** into the PR body. Read `$AGENT_DIR/review/test-findings.md` if present for Test Results / Acceptance Criteria. If there is no spec, derive Summary and Changes from the commit log and `--stat` diff.

Always add a **Testing Notes** (Заметки для тестирования) section — main scenario, edge cases, out-of-scope.

---

## Step 4: Create the Pull Request

```bash
gh pr create --base main --head "$BRANCH" \
  --title "<краткое описание задачи>" \
  --body "$(cat <<'EOF'
## Описание
<что сделано — 1-3 предложения>

## Spec
.agent/runs/<task-id>/spec.md — выбранный подход + API-контракт
<!-- опустить, если spec.md нет -->

## Изменения
- <ключевые изменённые файлы / компоненты>

## Результаты тестов
- Backend: pytest X/Y · Frontend: vitest X/Y
<!-- из review/test-findings.md, если есть -->

## Критерии приёмки
- [ ] <Must-have / acceptance criterion 1>
- [ ] <Must-have / acceptance criterion 2>

## Заметки для тестирования
- Основной сценарий: <описание>
- Edge cases: <что может пойти не так>
- Вне скоупа: <что не нужно проверять>
EOF
)"
```

Capture the PR URL.

---

## Step 5: Post open Human-Decision items as PR comments

If `$AGENT_DIR/review/findings.md` exists and has open `[H-xxx]` items, post each one as a PR comment:

```bash
gh pr comment "$BRANCH" --body "[H-xxx] <the open human-decision item>"
```

---

## Step 5.5: Move the GitHub Issue to In review

Per the invariant "PR open → In review", move the linked issue on the board:

```bash
python scripts/implement-pipeline.py set-status <task-id> in-review
```

---

## Step 6: Report

Give the user a tight report:
- PR URL
- Branch
- Number of H-items posted (if any)

---

## Rules

- Never merge automatically.
- Never push to `main`; never ship from `main`.
- Never commit code. If the tree is dirty, stop and ask the user to commit first.
- Russian PR title + body.
- Coordination files live in the gitignored `.agent/runs/<task-id>/`; never write the committed `.agent/` planner.
