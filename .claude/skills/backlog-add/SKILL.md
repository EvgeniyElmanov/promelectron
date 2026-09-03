---
name: backlog-add
description: Add an idea/TODO to the project backlog as a GitHub Issue on AutonomaCo/promelectron, then place it on the GitHub Project board (Todo). Interactive — capture a quick one-liner, or spin up a background agent that enriches the idea with current session context before the issue is finalized.
argument-hint: "<идея / TODO для бэклога>"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(gh *) Bash(jq *) Bash(git *)
---

# /backlog-add — Capture an idea into the GitHub backlog

The **backlog is GitHub Issues** on the repo `AutonomaCo/promelectron`, organized on the
**GitHub Project (v2)** board. This command creates a new Issue from an idea/TODO and (optionally)
adds it to the board so it lands in the **Todo** column. There is **no local backlog file** here —
do not write any. (The committed `.agent/BACKLOG.md` sprint planner is a *separate* human-managed
artifact — `/backlog-add` never touches it.)

You can capture the idea as a **quick one-liner**, or spin up a **parallel background agent** that
expands it into a richer issue body using the context of the current session (what we were just
doing, which files/decisions are relevant) so a future feature starts with real context instead of
a bare title.

## Input: $ARGUMENTS

The idea text. If empty, ask the user what they want to capture and wait.

## Pipeline

### Step 1: Locate the repo & sanity-check `gh`

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
gh auth status   # must be authenticated; the repo is AutonomaCo/promelectron
```

Adding it to the **Project board** needs the `project` token scope. If a `gh project …` call
returns `missing required scopes` (e.g. `[read:project]` / `[project]`), STOP the board step and
tell the user (Russian) to run, in their own shell (it is interactive — you cannot do it):

```
gh auth refresh -s project
```

Creating the Issue itself needs only normal repo scope — never block issue creation on the project
scope. Worst case the issue is created but not placed on the board; report that honestly.

### Step 2: Derive a concise title

From the idea text, distill a tight one-line **title** (Russian if the idea is Russian). The full
idea goes in the body. Optionally pick 0–2 light **labels** (only if they obviously apply and exist
on the repo — `gh label list`; don't invent labels).

### Step 3: Ask short vs. enrich (INTERACTIVE — the core)

Use `AskUserQuestion` (in Russian):

> **Как завести идею «<title>» в бэклог?**
> - **Коротко** — создать issue как есть: краткий заголовок + идея в теле. Быстро.
> - **Развернуть агентом (параллельно)** — issue создаётся сразу (идея не потеряется), а фоновый
>   агент возьмёт идею + релевантный контекст текущей сессии и распишет тело шире (проблема,
>   набросок подхода, что трогать, открытые вопросы), затем обновит issue. Можешь продолжать
>   работать — агент допишет в фоне.

### Step 4a: Short path

Create the issue immediately:

```bash
gh issue create --repo AutonomaCo/promelectron \
  --title "<title>" \
  --body "$(cat <<'EOF'
<the idea text, lightly cleaned>

---
_Заведено через /backlog-add._
EOF
)" \
  --label "<label>"   # repeat --label per label, or omit
```

Capture the returned issue **URL** and **number** `<N>`. Go to Step 5 (add to board), then report.

### Step 4b: Enrich path (create now, expand in background)

The idea must **never be lost**, so create the issue first, then let a background agent improve it.

1. **Distill the session context brief yourself first.** You (the main agent) hold the current
   session's context — the background agent does NOT. Write a tight **context brief**: what we were
   just working on, the task/feature/files involved, relevant decisions or constraints, and *why
   this idea came up*. This brief is the whole point of the enrich path.
2. **Create the issue now** (so it exists even if the agent fails), seeding the body with the idea +
   your context brief and a marker that enrichment is in flight:

   ```bash
   gh issue create --repo AutonomaCo/promelectron \
     --title "<title>" \
     --body "$(cat <<'EOF'
   <the idea text>

   ## Контекст (из сессии)
   <the context brief you distilled>

   > ⏳ Агент дорабатывает описание в фоне.
   EOF
   )" \
     --label "<label>"
   ```

   Capture the issue **number** `<N>` and **URL**.
3. Do Step 5 (add to board) now — don't wait for the agent.
4. **Launch a background `general-purpose` subagent** (`run_in_background: true`, so control returns
   to the user). Prompt:

   ```
   Expand a GitHub Issue (a backlog idea) into a richer body. Read-only on the codebase — your
   ONLY mutation is editing the one issue named below via `gh issue edit`.

   Repo: AutonomaCo/promelectron        Issue: #<N>
   Idea (title): <title>
   Raw idea text: <the idea text>
   Session context brief (from the main session — use this, it's the valuable part):
   <the context brief you distilled>

   Project root: <PROJECT_ROOT>
   You MAY read code under the project root (and use WebSearch/context7 to ground the approach),
   but stay tight — this is a backlog note, not a spec.

   Read the current issue first: gh issue view <N> --repo AutonomaCo/promelectron --json title,body
   Then rewrite the body and apply it:
     gh issue edit <N> --repo AutonomaCo/promelectron --body "$(cat <<'EOF'
     ## Проблема / зачем
     <problem + motivation>
     ## Набросок подхода
     <rough direction, files/modules to touch, candidate approach>
     ## Что трогать
     <touchpoints — services, endpoints, components likely involved>
     ## Открытые вопросы
     <what to decide/verify before building — omit the section if none>
     EOF
     )"
   Remove the "⏳ Агент дорабатывает…" marker. Do NOT change the title or labels unless clearly wrong.

   Return a 2-3 line summary of what you captured.
   ```

5. Tell the user the issue is created and being enriched in the background; they can keep working —
   the body will be finalized when the agent returns.

### Step 5: Add the issue to the Project board (Todo)

So the idea shows up in `/backlog-list` grouped under **Todo**, add it to the board. Load the
**`github-project`** skill for project/owner discovery and the exact commands; in short:

```bash
gh project item-add <projectNumber> --owner <owner> \
  --url https://github.com/AutonomaCo/promelectron/issues/<N>
```

`item-add` lands the card in the board's default column (typically **Todo**), which is what we
want for a fresh backlog idea — no status move needed. If the project has no default-status
automation and the card needs an explicit `Todo`, use the `github-project` skill's `item-edit` to
set Status → Todo. If the `project` scope is missing, skip this step and tell the user (Step 1).

### Step 5b: Put it on the launch board

The board `ai-launcher/BOARD.md` is the **shop window** of the open issues — a new issue that
never reaches it is invisible to `/board` and `/sessions`, and to the colleague working on the
other agent. Add a row to the Указатель table: issue number, one line of what it is, its **lock**
(see `.claude/rules/task-locks.md`), status.

Add **no button** — a button only exists for an item that has a prompt in `ai-launcher/prompts/`.
The fresh issue goes under «заведено, но кнопки нет» until someone writes one.

Board format, lock table and the pre-commit form check: `ai-launcher/CONVENTIONS.md`.

### Step 6: Report (in Russian)

- `✓ В бэклог: #<N> «<title>»` + the issue URL.
- Board: `на доске → Todo` — or, if scope was missing, `issue создан, но на доску не добавлен
  (нужен scope project: gh auth refresh -s project)`.
- Short path → "готово." Enrich path → "разворачиваю в фоне, тело допишется когда агент закончит."
- Board: `на пульте → ai-launcher/BOARD.md` (без кнопки — промпта пока нет).
- Hint: `/backlog-list` чтобы посмотреть весь бэклог · `/board` — пульт запуска · `/implement <N>` чтобы взять в работу.

## Rules

1. **GitHub backlog only.** Issues live on `AutonomaCo/promelectron` + the Project board. There is
   **no local backlog file** to write — never write `.agent/BACKLOG.md` or any `.agent/backlog/`.
2. **Interactive** — always offer short vs. enrich; never silently pick one.
3. **Never lose the idea.** On the enrich path, create the issue *before* launching the background
   agent; the agent only edits an already-existing issue.
4. **Enrich = parallel + context.** The background agent's value is the session context YOU pass it.
   Distill the brief before launching; don't hand it a bare title.
5. **Don't block issue creation on board scope.** Issue creation needs only repo scope; if the
   `project` scope is absent, create the issue anyway and report that the board wasn't updated.
6. **Idempotent-ish.** If the user re-runs for the same idea, don't duplicate — point at the
   existing issue if you can tell it's the same; otherwise create.
