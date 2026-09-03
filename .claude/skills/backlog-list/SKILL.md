---
name: backlog-list
description: Show the project backlog — open GitHub Issues on AutonomaCo/promelectron grouped by their GitHub Project board status column (Todo / In Progress / In Review / Done). Optional filter by status column or label. Read-only — never mutates issues or the board. May surface the committed .agent/BACKLOG.md sprint planner as secondary context.
argument-hint: "[фильтр: Todo|In Progress|In Review|Done|<label>]"
disable-model-invocation: true
allowed-tools: Read Bash(gh *) Bash(jq *) Bash(git *)
---

# /backlog-list — Show the GitHub backlog

The **backlog is GitHub Issues** on `AutonomaCo/promelectron`, organized on the **GitHub Project
(v2)** board. This command lists open issues **grouped by their board status column**
(Todo / In Progress / In Review / Done) so you see the whole backlog at a glance. It is
**read-only** — listing never changes an issue or moves a card.

## Input: $ARGUMENTS

Optional filter. If empty — show everything grouped by status column. Otherwise:
- a **status column** (`Todo`, `In Progress`, `In Review`, `Done`) → show only that column,
- anything else → treat as a **label** and filter issues by it.

## Pipeline

### Step 1: Sanity-check `gh` & discover the board

```bash
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
gh auth status
```

Reading the board needs the `read:project` (or `project`) scope. If a `gh project …` call returns
`missing required scopes`, tell the user (Russian) to run, in their own shell (interactive):

```
gh auth refresh -s project
```

Load the **`github-project`** skill to discover the project number/owner and the **Status** field,
and to map each board item → its status column.

### Step 2: Pull issues + their board status

1. Open issues on the repo (source of titles/labels/urls):
   ```bash
   gh issue list --repo AutonomaCo/promelectron --state open --limit 200 \
     --json number,title,labels,url
   ```
2. Board items with their Status column (the grouping key):
   ```bash
   gh project item-list <projectNumber> --owner <owner> --format json --limit 500 \
     | jq -r '.items[] | {num: .content.number, status: .status, title: .content.title}'
   ```
   Join on issue **number**: an issue's group is its board **Status** column. Issues open but
   **not on the board** go under a `(не на доске)` group so they're never hidden. (If the
   `github-project` skill exposes a cached field mapping, use it; otherwise read `status` from
   `item-list` directly.)

Apply the `$ARGUMENTS` filter (status column or label) if given.

### Step 3: Render (grouped by column)

Order columns by workflow: **Todo → In Progress → In Review → Done** (Done collapsed). Example:

```
Бэклог Promelectron (GitHub Issues · открытых <M>)

TODO
  #42  Кэшировать ответы offer-сервиса            [offer, perf]
  #45  Ретраи в payment-клиенте                   [payment]
IN PROGRESS
  #38  Гостевая корзина: merge при login          [frontend]
IN REVIEW
  #40  ЮKassa webhook подпись                      [backend]  → PR #51
DONE
  (свернуто, N штук)
(не на доске)
  #46  Добавить .dockerignore в backend/
```

If the user wants one issue's detail (or there are few), show its body:
`gh issue view <N> --repo AutonomaCo/promelectron`.

### Step 4: Point at the launch board

`ai-launcher/BOARD.md` is the **shop window** of this same issue list — it is where an item gets a
lock, a status and a ready-to-paste launch button. After the listing, name any open issue that is
**not** on the board (it will be invisible to `/board` and `/sessions`, and to the colleague on the
other agent) and offer `/board refresh` to reconcile. Don't rewrite the board from here — listing
is read-only.

### Step 5: Secondary context — local sprint planner (read-only)

Optionally, after the GitHub list, surface the committed **`.agent/BACKLOG.md`** sprint planner
(the Kimi system) as a separate **«локальный план (спринт)»** section — a brief, read-only digest
(current sprint goal + a few P0 rows). Make clear it is a *different* artifact from the GitHub
backlog (human-managed sprint planning), not the issue list. Never edit it.

### Step 6: Interactive handoff (Russian — light touch)

After listing, offer (don't force):

> "Взять задачу в работу — `/implement <issue#>` (полный цикл: spec → разработка → PR) или
> `/backlog-pick <issue#>` чтобы сначала развернуть в задачу. Добавить идею — `/backlog-add`.
> Пульт запуска с кнопками и замками — `/board`; какие сессии открывать сейчас — `/sessions`."

If the user names an issue to act on, you may hand off to `/implement` / `/backlog-pick` directly
rather than making them re-type.

## Rules

1. **GitHub backlog only.** The backlog *is* GitHub Issues + the Project board. `.agent/BACKLOG.md`
   is shown only as **secondary, read-only** context — it is not this backlog.
2. **Read-only — always.** Listing never creates/edits/closes an issue and never moves a card.
   Status changes belong to `/implement` (which moves cards) and the human.
3. **Group by board status.** Todo / In Progress / In Review / Done from the GitHub Project; surface
   open issues not yet on the board under `(не на доске)` so nothing is hidden.
4. **Fail honest on scope.** If `read:project` is missing, say so and tell the user how to fix it
   (`gh auth refresh -s project`) rather than silently dropping the grouping — you can still list
   raw issues from `gh issue list`, just without the columns.
