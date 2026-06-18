# 📘 HOWTO — Working with Promelectron agents in Kimi Code CLI

> Practical guide: how to route tasks, keep context clean, and pick the right workflow.

## 1. Problem we solved

Kimi Code CLI discovers project skills from `.kimi-code/skills/`. We moved all workflow skills there so `/implement`, `/fix`, `/review`, and `/deploy` work out of the box.

## 2. Three ways to work

### Way A: Workflow skills (recommended)

Use for full feature cycles, bug fixes, reviews, and deploys.

```
/implement "Add promo codes to cart"
/fix "Race condition in cart add"
/review
/deploy test
```

The skill spawns subagents and manages the pipeline for you.

### Way B: Fixed role

Use if you work in one role all day.

```
Role: backend-dev. Task: add email validation to registration.

Read PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md, SESSION_LOG.md.
Read .kimi/agents/backend-dev.md and .kimi/rules/pre-edit-checklist.md.
After work update SESSION_LOG.md.
```

### Way C: Dispatcher (ad-hoc tasks)

Use when you don't know the role and don't need a full workflow.

```
Read .kimi/agents/dispatcher.md and follow its instructions strictly.
Task: Create an API for promo codes.
```

## 3. How `/implement` works

1. Creates `.agent/<task-id>/`
2. Spawns architect subagent in plan mode → writes `spec.md` → waits for approval
3. Creates git worktree `.worktrees/implement-<task-id>` on branch `feature/<task-id>`
4. Spawns developer subagent(s) in the worktree
5. Spawns code reviewer subagent → writes `review/findings.md` (max 3 iterations)
6. Spawns QA/e2e-tester subagent → writes `review/test-findings.md`
7. Reports to user; merge only with explicit approval

## 4. Bash helpers

```bash
make check            # lint + test
make dev              # start the stack
make stop             # stop the stack
make test-backend     # backend tests (PostgreSQL in Docker)
make test-frontend    # frontend unit tests
make test-e2e         # Playwright E2E tests
make status           # git + services
```

Pipeline helper:

```bash
python scripts/implement-pipeline.py setup "Add promo codes to cart"
python scripts/implement-pipeline.py create-worktree <task-id>
python scripts/implement-pipeline.py cleanup <task-id>
```

## 5. How to tell the role switched

When using the dispatcher or a workflow skill, the subagent should state its role at the start. If the agent answers in the wrong style, reload the skill or start a new session.

## 6. Roles and zones

| Role | Zone |
|------|------|
| `backend-dev` | `backend/src/app/`, `backend/tests/` |
| `frontend-dev` | `frontend/src/` |
| `devops` | `infra/`, `.github/workflows/` |
| `e2e-tester` | `frontend/e2e/` |
| `code-reviewer` | diff → findings |
| `security-reviewer` | security findings |
| `project-manager` | plans, backlog, roadmap |
| `qa` | full test pyramid |
| `integration-dev` | local dev environment |

## 7. Required files

Agents read:
- `PROJECT_CONTEXT.md`
- `.agent/BACKLOG.md`
- `.agent/BLOCKERS.md`
- `.agent/SESSION_LOG.md`
- `.kimi/agents/<ROLE>.md`
- `.kimi/rules/pre-edit-checklist.md`

Agents update:
- `.agent/SESSION_LOG.md`
- `.agent/BACKLOG.md`
- `.agent/BLOCKERS.md`
- `PROJECT_CONTEXT.md` (if architecture changed)

## 8. Troubleshooting

### Skill is not recognized
- Verify `.kimi-code/skills/` exists and contains `SKILL.md` files.
- Kimi Code CLI loads skills automatically from `.kimi-code/skills/`.

### Agent doesn't switch role
1. Reload the workflow skill: `/implement ...`
2. Start a new Kimi CLI session
3. Explicitly specify the role: `Role: frontend-dev. Task: ...`

### `make task` / `make ask` removed
The old `make task`, `make ask`, `make auto`, and `make task-compact` helpers were removed. Use workflow skills instead:
```
/implement "Add promo codes to cart"
/fix "Race condition in cart add"
/promelectron
```

### Agent didn't update SESSION_LOG.md
In workflow skills this is part of the subagent prompt. In fixed-role mode, add it explicitly:
```
After work update SESSION_LOG.md.
```

## 9. Task format (5 elements)

```
[ROLE] Task: [one sentence]
File: [specific file or zone]
Related: [related files that will also change]
Do not break: [boundaries]
Verify: [how to confirm it works]
```

See `.kimi/rules/prompt-format.md` for details.

## 10. Quick-start checklist

- [ ] Open Kimi CLI in the project root
- [ ] Run `/implement "<feature description>"`
- [ ] Approve the architect's spec
- [ ] Let the pipeline run
- [ ] After completion check `.agent/SESSION_LOG.md`

## 11. Where to read more

- [SESSION_START.md](/SESSION_START.md) — session entry templates
- [AGENTS.md](/AGENTS.md) — agent index, skills, rules, permissions
- [ROUTER.md](/ROUTER.md) — routing documentation
- `.kimi/rules/pre-edit-checklist.md` — checks before editing code
