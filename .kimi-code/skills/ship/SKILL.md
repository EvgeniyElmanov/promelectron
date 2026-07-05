---
name: ship
description: >
  Open a GitHub Pull Request from the current feature branch.
  For when the code is already written and committed and you just want to ship the PR.
  Derives the task-id from the branch, pulls Must-haves from the task's spec,
  builds the PR body, runs pre-push checks, pushes if needed, creates the PR,
  and posts open [H-xxx] items as PR comments.
type: prompt
whenToUse: When the user asks to open a PR, ship a feature, create a pull request, or when /skill:implement would normally create a PR.
arguments: "[task-id|branch] (optional — defaults to the current branch)"
disableModelInvocation: false
---

# /skill:ship — Создание GitHub Pull Request

> **ЯЗЫК / LANGUAGE:** Пользователь общается на русском. Все ответы пользователю, title/body PR и артефакты пиши на русском. Стремись рассуждать на русском, но если reasoning уходит на английский — это не ошибка; главное, чтобы финальные ответы и артефакты были на русском. Код, команды, идентификаторы, пути и технические термины оставляй в оригинале.

Создай GitHub PR из **текущей feature-ветки**, используя шаблон проекта. Это автономная версия Step 8 из `/skill:implement` — для случая, когда код уже написан, закоммичен, и нужно просто открыть PR.

## Language / Язык

Следуй [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule / Языковое правило. Title и body PR пиши на русском при русскоязычном пользователе.

---

## Step 0: Предварительные проверки

Проверь доступ к GitHub CLI:

```bash
gh auth status
gh project view 1 --owner AutonomaCo
```

Если что-то не так — остановись и попроси пользователя выполнить `gh auth login` или выдать scope `project`.

---

## Step 1: Определение контекста

Текущая директория может быть основным репозиторием или git worktree. Всегда определяй корень **основного репозитория**, потому что `.agent/runs/` живёт только там:

```bash
# Внутри worktree эта команда вернёт путь к worktree; нам нужен main repo.
ANY_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_ROOT="$(git -C "$ANY_ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null | xargs dirname 2>/dev/null || echo "$ANY_ROOT")"
```

Если выше не работает в твоей версии git, используй fallback:

```bash
PROJECT_ROOT="$(git -C "$ANY_ROOT" rev-parse --show-toplevel 2>/dev/null || echo "$ANY_ROOT")"
```

Определи ветку и task-id:

```bash
CURRENT_BRANCH="$(git -C "$ANY_ROOT" branch --show-current)"
```

Если task-id или ветка переданы аргументом:
- Если начинается с `feature/` или `bugfix/` → используй как ветку и выведи `task-id` из суффикса.
- Иначе считай `task-id`; ветка ожидается как `feature/<task-id>` или `bugfix/<task-id>`.

Если аргумент не передан, используй `CURRENT_BRANCH`.

Если ветка `main` (или detached HEAD), остановись и спроси пользователя, какую ветку ship.

Убедись, что текущий checkout соответствует ветке для ship. Если нет:
- Вариант A: `git -C "$ANY_ROOT" checkout "$BRANCH"` (с одобрения пользователя).
- Вариант B: остановись и попроси пользователя переключиться на нужную ветку.

Установи `AGENT_DIR = $PROJECT_ROOT/.agent/runs/<task-id>`.

Получи diff относительно `origin/main`:

```bash
git -C "$ANY_ROOT" fetch origin
git -C "$ANY_ROOT" log origin/main..HEAD --oneline
git -C "$ANY_ROOT" diff origin/main...HEAD --stat
```

If there are no commits to ship, tell the user and stop.

---

## Step 2: Ensure the branch is up-to-date with origin/main

```bash
git -C "$ANY_ROOT" fetch origin main
git -C "$ANY_ROOT" log HEAD..origin/main --oneline
```

If `origin/main` has commits not in the current branch, warn the user and ask whether to rebase/merge before shipping.

---

## Step 3: Run pre-push checks

`AGENTS.md` requires `make pre-push` (lint + unit tests + E2E) before pushing a feature branch.

```bash
make -C "$ANY_ROOT" pre-push
```

If pre-push fails, stop and report failures. Do NOT open a PR with failing checks.

---

## Step 4: Ensure everything is pushed

1. `git -C "$ANY_ROOT" status --porcelain` — if there are uncommitted changes, stop and tell the user to commit or stash first. `/skill:ship` does not commit code.
2. Check for unpushed commits: `git -C "$ANY_ROOT" log @{u}..HEAD --oneline 2>/dev/null` (or `origin/<branch>..HEAD` if no upstream). If there are unpushed commits — or no upstream — push:
   ```bash
   git -C "$ANY_ROOT" push -u origin "$BRANCH"
   ```

---

## Step 5: Gather the PR body

Read `$AGENT_DIR/spec.md` if it exists and pull its **Must-haves** and **Acceptance Criteria** into the PR body. Read `$AGENT_DIR/review/test-findings.md` if present for Test Results. If there is no spec, derive Summary and Changes from the commit log and `--stat` diff.

Always add a **Testing Notes** (Заметки для тестирования) section — main scenario, edge cases, out-of-scope.

---

## Step 6: Create the Pull Request

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

Capture the PR URL. If `gh pr create` fails, stop and report the error; do not attempt to post comments or update board status.

---

## Step 7: Post open Human-Decision items as PR comments

If `$AGENT_DIR/review/findings.md` exists and has open `[H-xxx]` items, post each one as a PR comment:

```bash
gh pr comment "$BRANCH" --body "[H-xxx] <the open human-decision item>"
```

---

## Step 8: Move the GitHub Issue to In review

Per the invariant "PR open → In review", move the linked issue on the board **only if** `$AGENT_DIR/task.md` exists and contains a linked issue:

```bash
python scripts/implement-pipeline.py set-status <task-id> in-review
```

If `set-status` fails, report the error but do not block on it.

---

## Step 9: Report

Give the user a tight report:
- PR URL
- Branch
- Pre-push results
- Number of H-items posted (if any)

---

## Rules

- Never merge automatically.
- Never push to `main`; never ship from `main`.
- Never commit code. If the tree is dirty, stop and ask the user to commit first.
- Always run `make pre-push` before opening PR.
- Russian PR title + body.
- Coordination files live in the gitignored `.agent/runs/<task-id>/`; never write the committed `.agent/` planner.
- Handle `gh pr create` errors gracefully.

---
