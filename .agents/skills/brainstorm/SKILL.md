---
name: brainstorm
description: Interactive research & brainstorming session. Explore a topic WITH the user — fan out parallel research sub-agents, synthesize the findings into an honest trade-off discussion, and save a study-friendly brainstorm.md to the per-task coordination plane. Input may be free text or a GitHub Issue. Pure exploration — writes no spec, no code, and never moves the GitHub Project board. Hands off to /architect or /implement.
argument-hint: "<тема / вопрос для изучения | issue#|gh-5>"
disable-model-invocation: true
allowed-tools: Read Write Edit Bash(git *) Bash(gh *) Bash(mkdir *) Task
---

# /brainstorm — Interactive Research & Brainstorm

Interactive **research & brainstorming** session. You explore a topic *with* the user — fan out
to study it in parallel, explain how things work, compare options with honest trade-offs — and
save a study-friendly artifact to `.agent/runs/<task-id>/brainstorm.md` that the user can later
feed to the architect (`/architect <task-id>` / `/implement <task-id>`).

This is **not** a spec and **not** production code. It's a learning/decision aid: "как работает
langgraph и чем он лучше PydanticAI", "какие есть варианты для очереди задач", "разберись как
устроен CDC у Debezium". The user reads it, picks a direction, and hands the chosen bits onward.

> **Coordination plane only.** Everything lives under `.agent/runs/<task-id>/` (gitignored — see
> the `pipeline-workspace` skill). **Never** write into the committed `docs/` planner
> (`BACKLOG.md`, `DECISIONS.md`, `tasks/` …) — that is a separate human planning system.
> This command is **pure exploration**: it writes no spec, no code, and **never moves the GitHub
> Project board**.

## Input: $ARGUMENTS

A topic, question, or comparison to explore — free text **or** a GitHub Issue (`5`, `#5`, `gh-5`,
or an issue URL). If empty, ask the user what they want to dig into and **wait**.

## Parallelism Model (read first)

Studying a topic splits cleanly into independent angles (each option, each sub-question, "how it
fits our codebase"). **Launch all research sub-agents in a single message with multiple Task
calls** so they run concurrently — that's the point. The interactive discussion and synthesis are
done by **you** (the main agent), because this is a conversation with the user; sub-agents can't
spawn sub-agents, so the fan-out happens here.

## Pipeline

### Step 1: Frame & prepare the workspace

1. Restate the goal in one sentence and confirm you understood it. If the topic is too vague to
   research well, ask 1–3 sharp clarifying questions and **wait** (e.g. "сравнить для какого
   сценария — оркестрация агентов или валидация ответа LLM?").
2. Record the repo root: `PROJECT_ROOT="$(git rev-parse --show-toplevel)"`.
3. Derive the `<task-id>`:
   - **GitHub Issue** → `gh-<N>`. Fetch it for context:
     `gh issue view <N> --json number,title,body,comments,url,labels`, and write
     `.agent/runs/gh-<N>/task.md` in the GitHub-Issue `task.md` format from the
     `pipeline-workspace` skill.
   - **Free text** → a short kebab-case slug (lowercase, hyphens, ~40 chars, e.g.
     `langgraph-vs-pydanticai`). Write the raw question to `.agent/runs/<slug>/task.md`
     (free-text format) so the artifact has provenance.
4. Create the research dir:
   ```bash
   mkdir -p "$PROJECT_ROOT/.agent/runs/<task-id>/research"
   ```
5. **Reuse an existing workspace.** If `.agent/runs/<task-id>/task.md` already exists (handed off
   from another command), do **NOT** regenerate it — read that `task.md` as the topic/brief and
   build on it. Only create a fresh `task.md` for a genuinely new topic.

### Step 2: Research fan-out (PARALLEL — single message, multiple Task calls)

Decompose the topic into independent angles and launch one `general-purpose` sub-agent per angle,
**all in one message**. Pick the decomposition that fits the question:

- **Comparison ("X vs Y")** → one agent per option (how X works, its model, strengths/limits) +
  optionally one agent for "head-to-head / what people actually pick and why".
- **"How does X work"** → split by sub-system or by depth (core concepts / API surface / gotchas
  & production concerns).
- **"What are the options for Z"** → one agent surveys the landscape, others go deep on the 2–3
  most promising candidates.

Use `general-purpose` (it reads the web, reads the repo, **and** writes its file); `Explore`
can't write, so don't use it here.

Prompt skeleton per angle:

```
You are researching ONE angle of a topic the user wants to understand. Read-only — do not edit
code or create anything outside your research file.

Topic: <the overall question>
Your angle: <e.g. "how LangGraph works: execution model, state, when you'd reach for it">
If relevant, how it'd fit this codebase: <absolute PROJECT_ROOT — FastAPI backend/, Vue 3 frontend/>

Use WebSearch/WebFetch for docs, patterns, opinions, and recent changes; read the repo for fit.
Prefer primary sources; note version/date when it matters (the ecosystem moves fast).

Write a tight, neutral brief to <PROJECT_ROOT>/.agent/runs/<task-id>/research/<angle>.md:
## How it works   (the mental model — concepts, not marketing)
## Strengths / Good fit
## Limits / Gotchas
## Sources   (URL — 1-line takeaway each)
Return a 3–4 line summary.
```

### Step 3: Synthesize & discuss (interactive — the core)

Read all `research/*.md`, then **talk it through with the user** in this conversation:

- Explain how each thing works in plain terms — mental model first, details second.
- For comparisons, give a **trade-off table** (axes that matter: learning curve, control vs
  magic, ecosystem, production-readiness, fit for our FastAPI/Vue stack) and **recommend one**,
  with the reasoning and the conditions under which you'd pick the other.
- Be honest about uncertainty and version-sensitivity. Don't oversell.
- Iterate: when the user asks a follow-up that needs fresh digging, spawn another targeted
  research sub-agent (or a small parallel batch) and fold the result into the discussion.

Keep going until the user is satisfied. The value is in the back-and-forth, not in rushing to a
file.

### Step 4: Save the artifact

Continuously (or when the user asks), write/update `.agent/runs/<task-id>/brainstorm.md` in a
**study-friendly** form — something the user can re-read later and skim quickly:

```markdown
# Brainstorm: <topic>

> **Вопрос:** <one line> · **TL;DR:** <1–2 sentence bottom line / recommendation>

## Как это работает
### <Option / concept A>
mental model, key pieces, when to reach for it
### <Option / concept B>
…

## Сравнение
| Критерий | A | B |
|----------|---|---|
| … | … | … |

## Trade-offs и рекомендация
What to pick, why, and when the other wins.

## Открытые вопросы
Things to decide / verify before building.

## Источники
- [<title>](<url>) — takeaway
```

Keep the `research/*.md` partials — they're the raw material behind the synthesis.

### Step 5: Handoff

Tell the user (in Russian):
- Path to `.agent/runs/<task-id>/brainstorm.md` and a 2–3 line summary.
- The recommendation and any open questions worth deciding before building.
- Offer the handoff: "Скормить выбранное архитектору? `/architect <task-id>` или
  `/implement <task-id>` подхватят `.agent/runs/<task-id>/`." If the user has converged on a
  direction, offer to write that decision into `.agent/runs/<task-id>/task.md` so the architect
  starts from it.

## Rules

1. **Interactive first** — never skip the discussion and just dump a file, unless the user
   explicitly says "просто запиши".
2. **Research in parallel** — angles fan out into concurrent sub-agents in one message; synthesis
   and conversation stay with you.
3. **Neutral and honest** — present trade-offs fairly, flag version-sensitivity, mark guesses.
   No marketing copy.
4. **This is exploration, not a spec** — you don't write production code or a technical spec
   here; you hand the chosen direction to the architect.
5. **Coordination plane only.** Lives in `.agent/runs/<task-id>/` (gitignored), adjacent to where
   the architect works, so the handoff is a one-liner. Never write the committed `docs/` planner.
6. **Never moves the GitHub Project board** — pure exploration has no board signal.
