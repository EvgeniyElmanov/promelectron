# Agent-First Rule

> Always delegate to specialized agents before doing work manually.

## When to Use Agents

You **MUST** use an agent (via `Agent` tool) when:

1. **The task requires >3 search queries** — exploring codebase, finding patterns, mapping dependencies
2. **The task spans >3 files** — refactoring, feature implementation, bug investigation
3. **A specialized agent exists** for the domain:
   - `project-manager` — planning, audits, roadmap updates, priority assessment
   - `backend-dev` — FastAPI, SQLAlchemy, migrations, services
   - `frontend-dev` — Vue 3, components, API integration
   - `code-reviewer` — quality checks, security review
   - `e2e-tester` — Playwright tests, visual regression
   - `tester` — unit tests, edge cases
4. **You are updating PLAN.md** — always delegate to `project-manager`
5. **You are doing a security audit** — delegate to `code-reviewer` or `security-reviewer`
6. **You are touching infra/docker/k8s** — delegate to `devops`

## When You MAY Skip Agents

You MAY work directly (without agent delegation) when:

1. **Single-file change** — typo fix, one-line bugfix, simple rename
2. **Reading a known file** — user explicitly asked for `file.py`
3. **Simple Q&A** — explaining a concept, answering about syntax
4. **Emergency fix** — production down, need immediate action (still document what agent would have caught)

## How to Delegate

1. **Choose the right agent** by matching the task domain to the agent description
2. **Provide full context** in the prompt — agents don't see your current conversation automatically
3. **Include relevant file paths** — don't make the agent search for what you already know
4. **Set explicit goals** — what should the agent deliver (file updates, findings report, code changes)
5. **Review agent output** — never blindly commit agent changes; verify correctness

## Anti-Patterns

- ❌ Manually exploring 10+ files to understand a module
- ❌ Updating PLAN.md without `project-manager` audit
- ❌ Writing backend code without checking if `backend-dev` agent has conventions
- ❌ Doing security review alone instead of `security-reviewer`
- ❌ Implementing a feature across backend+frontend as one giant step

## Rationale

Agents are specialized sub-processes with:
- **Fresh context** — no compactions, no drift from previous tasks
- **Focused execution** — single goal, no distractions
- **Reproducible results** — same prompt → same workflow → consistent quality
- **Parallel execution** — multiple agents can work simultaneously on independent tasks

Your manual work should be **coordination, review, and final decisions** — not raw exploration and implementation.
