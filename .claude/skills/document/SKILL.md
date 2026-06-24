---
name: document
description: Research a topic IN PARALLEL and synthesize a concise Markdown doc (runbook, data dictionary, architecture note, onboarding). Fans out read-only general-purpose sub-agents — one per relevant axis (Codebase, Database, Web, GitHub) — in a single message, each writing one research partial under the scratchpad workspace, then a single synthesis pass writes the final doc. Everything lives under the scratchpad dir; nothing is committed and no PR is created.
argument-hint: "<что задокументировать; можно с #issue / PR-ссылками и явным scope>"
disable-model-invocation: true
allowed-tools: Read Write Bash(mkdir *) Bash(ls *) Bash(gh *) Task WebSearch WebFetch
---

# /document — Parallel research → concise Markdown doc

Research a topic **in parallel** and produce one concise Markdown document. Use this when the user
wants a doc/runbook/data-dictionary/onboarding note that requires digging through the repo, the
database, the web, and/or GitHub — and wants the gathering done **concurrently**.

The artifact is **always written under the scratchpad dir** — workspace
`/private/tmp/claude-503/-Users-ai-AutonomaCo-promelectron/eb60ba29-9f2f-4634-86b6-f9e2ca775289/scratchpad/<slug>/`
and final doc `…/scratchpad/<slug>.md`. **Nothing is committed and no PR is created.** This command
produces a local document, full stop.

## Input: $ARGUMENTS

Free-form description of what to document. May embed a GitHub issue/PR reference (`#42`, a PR URL),
table/service/module names, and an explicit scope (e.g. *«нас интересуют только заказы и оплаты»*).
If no input is given, ask the user **what** they want documented, **for whom** (audience), and the
**scope**.

## Isolation & parallelism model (read first)

- **Gather concurrently.** Information gathering splits cleanly along sources (codebase, database,
  web, GitHub). Launch all applicable research sub-agents **in a single message with multiple Task
  calls** so they run at the same time. This concurrency is the whole point of the command.
- **Synthesize once.** After the research partials land, a **single** synthesis pass reads them all
  and writes the final document. Sub-agents cannot spawn sub-agents, so the fan-out happens here in
  the orchestrator, then the synthesis is one pass.
- **Everything under the scratchpad dir.** Workspace `<SCRATCH>/<slug>/`, research partials in
  `<SCRATCH>/<slug>/research/`, final doc `<SCRATCH>/<slug>.md`. Never `/tmp`, never the repo.

## Pipeline

### Step 1: Prepare the workspace

1. **Derive a slug** from the topic: lowercase, spaces→hyphens, max ~40 chars
   (e.g. `orders-payments-flow`).
2. **Create the workspace** under the scratchpad dir:
   ```bash
   SCRATCH="/private/tmp/claude-503/-Users-ai-AutonomaCo-promelectron/eb60ba29-9f2f-4634-86b6-f9e2ca775289/scratchpad"
   WORKSPACE="$SCRATCH/<slug>"
   RESEARCH_DIR="$WORKSPACE/research"
   OUTPUT="$SCRATCH/<slug>.md"
   mkdir -p "$RESEARCH_DIR"
   ```
3. **Write `task.md`** to `$WORKSPACE/task.md`: the raw user request + audience + the explicit scope.
   If the input references a **GitHub issue/PR**, also fetch its context now and fold it in
   (`gh issue view <N>` / `gh pr view <N>`). The synthesis pass uses `task.md` to lock audience and
   scope.

### Step 2: Plan the research axes

Pick **only the axes that matter** for this request:

| Axis | File | Looks at |
|------|------|----------|
| Codebase | `research/codebase.md` | the repo — models, schemas, services, routes, when/where records are written, enums, business logic |
| Database | `research/database.md` | live schema — columns, types, nullability, FKs, enum/status values (via the project's DB access; SELECT-only) |
| Web / external | `research/web.md` | external standards/formats/libraries — only if the topic depends on them |
| GitHub | `research/github.md` | relevant issues/PRs (`gh issue view`, `gh pr view`, `gh search`) — decisions, history, open threads — when useful |

A pure-repo doc may need only `codebase`; a data-dictionary usually needs `codebase` + `database`;
a "why was it built this way" doc benefits from the `github` axis. **Don't spawn axes that add
nothing.** (There is no Yandex Tracker / Yandex wiki axis in this project.)

### Step 3: Research fan-out (PARALLEL — single message, multiple Task calls)

Launch one **`general-purpose`** sub-agent per chosen axis, **all in one message** so they run
concurrently. Each is read-only and writes its own file — they never collide. Use `general-purpose`
(it can read the repo, query the DB, browse the web, run `gh`, AND write its file); `Explore` cannot
write, so don't use it here.

Prompt skeleton per axis:

```
You are gathering research on ONE axis for an upcoming Markdown document. Read-only — do NOT
edit project code, do NOT commit, do NOT open a PR.

Topic / request: <one-paragraph topic + the user's instructions>
Scope (hard limit): <e.g. "only the orders and payments tables — ignore everything else">
Task context: <SCRATCH>/<slug>/task.md
Repo to explore (if relevant): /Users/ai/AutonomaCo/promelectron   (confirm cwd if ambiguous)

Axis: <axis name + exactly what to find>
<axis-specific hints — see below>

Write a tight, factual summary to <SCRATCH>/<slug>/research/<file>.md using:
## Sources   (file path / URL / issue-PR number — 1-line takeaway each)
## Findings  (the facts: for data, list columns with type/nullability/meaning; for code, the
             functions/events that write each record; cite exact paths)
## Open questions / gaps
Return a 2-3 line summary of what you found.
```

Axis-specific hints to include in the relevant prompts:

- **Codebase:** "Find where the in-scope entities are defined (SQLAlchemy models / Alembic
  migrations / Pydantic schemas) and **when each record is written or updated** — the event /
  service method / Celery task matters as much as the schema. Note enum values and their meaning.
  Cite exact file paths under `backend/` and `frontend/`."
- **Database:** "Inspect the live schema for in-scope tables — exact column types, nullability, FKs,
  and enum/status values; read a few sample rows. SELECT only — never mutate. Prefer the project's
  documented DB access (compose/test DB) over guessing from code."
- **Web / external:** "Cover only external standards/formats/libraries the topic depends on (e.g. a
  payment-provider webhook format). Cite URLs. Skip if the topic is purely internal."
- **GitHub:** "Use `gh` to pull the relevant issues/PRs (`gh issue view <N>`, `gh pr view <N>`,
  `gh search issues/prs`). Capture decisions, rationale, and still-open threads. Cite issue/PR
  numbers and URLs."

Pass each sub-agent the **absolute repo path** (`/Users/ai/AutonomaCo/promelectron`) to explore;
confirm with the user if the target project is ambiguous.

After all sub-agents return, verify each `research/*.md` exists and is non-empty. If an axis came
back thin, re-run just that one.

### Step 4: Synthesize the document (single pass)

Read every `$RESEARCH_DIR/*.md` plus `$WORKSPACE/task.md` and write the final document to
`$OUTPUT`. Lock audience and scope from `task.md`. Format per the request — **data dictionary** |
**runbook** | **architecture note** | **onboarding** — «максимально ёмко и информативно».
Cross-reference the research partials, **cite sources** (paths / URLs / issue-PR numbers), and flag
real gaps as `TODO`. Do not invent data facts — column types, enum values, "when is this written"
must come from the research, not from memory.

### Step 5: Report (in Russian)

Tell the user **in Russian**:
- Path to the final doc: `<SCRATCH>/<slug>.md`.
- A 2–3 line summary of what it covers.
- Any `TODO` / open gaps flagged during synthesis.
- Offer: **«Скопировать документ в `docs/`? (по умолчанию оставляю в scratchpad)»** — copy into the
  repo's `docs/` **only if the user asks**.

## Important rules

1. **Always write under the scratchpad dir** — never commit the artifact, never open a PR. This
   command only produces a local document.
2. **Gather in parallel** — research axes fan out into concurrent `general-purpose` sub-agents in
   one message; only the final synthesis is a single pass.
3. **Respect the user's scope** — if they said "only X and Y", every sub-agent and the synthesis
   stay inside that boundary.
4. **Don't guess data facts** — column types, enum values, and "when is this written" come from
   code/DB/GitHub, not from memory; unknowns become `TODO`.
5. **Pick axes deliberately** — only spawn the sources that actually inform this doc. The available
   axes here are **Codebase, Database, Web, and GitHub** (no Yandex Tracker / wiki).
