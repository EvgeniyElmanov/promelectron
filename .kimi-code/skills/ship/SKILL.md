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

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило. Title и body PR пиши на русском при русскоязычном пользователе.

---

## Ограничения API (Kimi K2.7-Code)

- Thinking mode обязателен (`thinking={"type":"enabled"}`); `reasoning_content` должен сохраняться между multi-turn tool calls (особенно при повторных попытках `gh pr create` / `git push`).
- Не считай переключение языка внутреннего рассуждения ошибкой. Главное — финальные ответы, title/body PR и артефакты на языке пользователя.
- `tool_choice` может быть только `"auto"` или `"none"`.
- Sampling-параметры фиксированы: `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`.

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

Если нет коммитов для ship — сообщи пользователю и остановись.

---

## Step 2: Актуализация ветки относительно основной ветки

```bash
git -C "$ANY_ROOT" fetch origin main
git -C "$ANY_ROOT" log HEAD..origin/main --oneline
```

Если в `origin/main` есть коммиты, которых нет в текущей ветке, предупреди пользователя и спроси, нужно ли rebase/merge перед shipping.

---

## Step 3: Запуск преддеплойных проверок

`AGENTS.md` требует `make pre-push` (lint + unit tests + E2E) перед push feature-ветки.

```bash
make -C "$ANY_ROOT" pre-push
```

Если pre-push падает — остановись и сообщи об ошибках. НЕ открывай PR с падающими проверками.

---

## Step 4: Убедиться, что всё отправлено в удалённый репозиторий

1. `git -C "$ANY_ROOT" status --porcelain` — если есть незакоммиченные изменения, остановись и скажи пользователю сначала закоммитить или stash. `/skill:ship` не коммитит код.
2. Проверь unpushed commits: `git -C "$ANY_ROOT" log @{u}..HEAD --oneline 2>/dev/null` (или `origin/<branch>..HEAD`, если нет upstream). Если есть unpushed commits — или нет upstream — запушь:
   ```bash
   git -C "$ANY_ROOT" push -u origin "$BRANCH"
   ```

---

## Step 5: Формирование описания запроса на слияние

Прочитай `$AGENT_DIR/spec.md`, если он есть, и вынеси его **Must-haves** и **Acceptance Criteria** в body PR. Прочитай `$AGENT_DIR/review/test-findings.md`, если есть, для раздела Результаты тестов. Если spec нет, выведи Описание и Изменения из commit log и `--stat` diff.

Всегда добавляй раздел **Заметки для тестирования** — основной сценарий, edge cases, вне скоупа.

---

## Step 6: Создание запроса на слияние

```bash
gh pr create --base main --head "$BRANCH" \
  --title "<краткое описание задачи>" \
  --body "$(cat <<'EOF'
## Описание
<что сделано — 1-3 предложения>

## Спецификация
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

Захвати URL PR. Если `gh pr create` падает — остановись и сообщи об ошибке; не пытайся оставлять комментарии или обновлять статус доски.

---

## Step 7: Публикация открытых вопросов, требующих решения человека

Если `$AGENT_DIR/review/findings.md` существует и содержит открытые пункты `[H-xxx]`, опубликуй каждый как комментарий к PR:

```bash
gh pr comment "$BRANCH" --body "[H-xxx] <открытый human-decision пункт>"
```

---

## Step 8: Перевести задачу GitHub в статус "На ревью"

Согласно инварианту "PR open → In review", переведи связанный issue на доске **только если** `$AGENT_DIR/task.md` существует и содержит связанный issue:

```bash
python scripts/implement-pipeline.py set-status <task-id> in-review
```

Если `set-status` падает, сообщи об ошибке, но не блокируйся на этом.

---

## Step 9: Итоговый отчёт

Сообщи пользователю краткий отчёт:
- PR URL
- Ветка
- Результаты pre-push
- Количество опубликованных H-items (если есть)

---

## Правила

- Никогда не мержи автоматически.
- Никогда не пушь в `main`; никогда не ship из `main`.
- Никогда не коммить код. Если рабочее дерево dirty — остановись и попроси пользователя сначала закоммитить.
- Всегда запускай `make pre-push` перед открытием PR.
- Title и body PR на русском.
- Coordination files живут в gitignored `.agent/runs/<task-id>/`; никогда не пиши в закоммиченную планировочную директорию `.agent/`.
- Обрабатывай ошибки `gh pr create` корректно.

---
