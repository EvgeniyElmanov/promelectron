# 🤖 AI Agent System — Promelectron

This project uses **Kimi Code CLI** skills and agent prompts stored in `.kimi-code/` and `.kimi/agents/`.

## Quick start

```bash
# Implement a new feature (full cycle)
/implement "Add promo codes to cart"

# Deploy to test or prod
/deploy test

# Review current changes
/review

# Fix failing tests
/fix-test
```

## Where things live

| Path | Purpose |
|------|---------|
| `.kimi-code/skills/` | Kimi-discoverable skills (`/implement`, `/fix`, `/review`, `/deploy`, `/context-sync`, `/plan-maintainer`, `/promelectron`) |
| `.kimi-code/mcp.json` | MCP server configuration (Playwright, Filesystem, Memory, Sequential Thinking, Kubernetes) |
| `.kimi-code/config.example.toml` | Example user-level Kimi Code CLI config (copy relevant sections to `~/.kimi-code/config.toml`) |
| `.kimi/agents/*.md` | Role prompts for subagents (architect, backend-dev, frontend-dev, code-reviewer, security-reviewer, e2e-tester, qa, devops, project-manager, integration-dev, dispatcher) |
| `.kimi/rules/*.md` | Shared rules: pre-edit checklist, golden path, dependency map, security, prompt format, task template |
| `scripts/implement-pipeline.py` | Helper for task IDs, git worktrees, and review-loop state |
| `.agent/<task-id>/` | Per-task working directory (`task.md`, `spec.md`, `review/findings.md`, `review/test-findings.md`) |
| `.worktrees/implement-<task-id>/` | Isolated git worktree for the feature branch |

## `/implement` pipeline

```
User: /implement "Add promo codes to cart"
        │
        ▼
   Create .agent/<task-id>/
        │
        ▼
   Architect subagent (plan mode)
   → reads context, asks questions, writes spec.md
   → ExitPlanMode → user approves
        │
        ▼
   git worktree add .worktrees/implement-<task-id> -b feature/<task-id>
        │
        ▼
   Developer subagent
   → backend-dev and/or frontend-dev in the worktree
        │
        ▼
   Code reviewer subagent (max 3 iterations)
   → writes .agent/<task-id>/review/findings.md
        │
        ▼
   QA / e2e-tester subagent
   → writes/updates E2E tests, runs pytest + vitest + Playwright
   → writes .agent/<task-id>/review/test-findings.md
        │
        ▼
   Report to user
   → merge only with explicit user approval
```

### Flags

- `--quick` — skip the architect/spec phase
- `--backend-only` — only backend development
- `--frontend-only` — only frontend development

## Agent registry

| Role | File | When to use |
|------|------|-------------|
| `architect` | `.kimi/agents/architect.md` | Design before implementation; writes `spec.md` |
| `backend-dev` | `.kimi/agents/backend-dev.md` | FastAPI/SQLAlchemy/service/route/tests |
| `frontend-dev` | `.kimi/agents/frontend-dev.md` | Vue 3/Pinia/composables/API/tests |
| `code-reviewer` | `.kimi/agents/code-reviewer.md` | Quality review after development |
| `security-reviewer` | `.kimi/agents/security-reviewer.md` | Security pass for auth/payments/webhooks/files/admin |
| `e2e-tester` | `.kimi/agents/e2e-tester.md` | Playwright UI validation |
| `qa` | `.kimi/agents/qa.md` | Full test pyramid + Acceptance Criteria |
| `devops` | `.kimi/agents/devops.md` | Helm, Docker, CI/CD, secrets |
| `project-manager` | `.kimi/agents/project-manager.md` | Roadmap, backlog, planning |
| `integration-dev` | `.kimi/agents/integration-dev.md` | Start/stop/diagnose local dev environment |
| `dispatcher` | `.kimi/agents/dispatcher.md` | Auto role selection for ad-hoc tasks |

## Rules (shared conventions)

| Rule | Description | Paths |
|------|-------------|-------|
| `.kimi/rules/pre-edit-checklist.md` | Checks before every code change | all code |
| `.kimi/rules/golden-path.md` | Critical user flows that must not break | all code |
| `.kimi/rules/dependency-map.md` | What to update when a file changes | all code |
| `.kimi/rules/security.md` | Security checklist | all code |
| `.kimi/rules/prompt-format.md` | Task format for agents | user prompts |
| `.kimi/rules/task-template.md` | Task template for backlog items | `.agent/tasks/` |

## MCP servers

Configured in `.kimi-code/mcp.json`:

- **Playwright** — browser automation for E2E tests
- **Filesystem** — project file access
- **Memory** — persistent knowledge graph
- **Sequential Thinking** — reflective problem solving
- **Kubernetes** — cluster introspection and operations

## Permissions

**Allowed:**
- `make *`, `pytest *`, `alembic *`, `ruff *`
- `git status`, `git diff`, `git log`, `git worktree *`, `git commit *` (feature branches only)
- `npm *`, `npx *`
- `docker *`, `kubectl *`, `helm *`
- `gh workflow run *`, `gh run *`

**Forbidden:**
- `rm -rf *`
- `git push --force *`
- `git reset --hard *`
- `DROP *`, `truncate *`

## Project context

`PROJECT_CONTEXT.md` is the single source of truth for stack, features, blockers, and API inventory. Every agent reads it at the start of a session. After significant changes, append a short note describing what changed.

## Red flags

- ❌ Create a DB model without an Alembic migration
- ❌ Write an endpoint without a test
- ❌ Delete an old component before the new one works
- ❌ Commit with `console.log` / `debugger`
- ❌ Commit without user approval
- ✅ Push to `main` only by explicit user request (normally use PR)

## Known pitfalls (Promelectron)

> Real issues that have already happened. Check before committing.

### 1. Tests must not touch dev/prod DB
`conftest.py` uses a separate test database. Always run `make test-backend` (PostgreSQL in Docker), never `pytest` locally on SQLite.

### 2. Rate limiting breaks tests
Reset the limiter in the `client` fixture.

### 3. SQLite ≠ PostgreSQL
Foreign keys, unique constraints, and SQL syntax differ. Test against PostgreSQL.

### 4. Trailing slash in FastAPI
`api.get('/categories/')` matches `@router.get("/")`. Missing trailing slash causes 307/CORS issues.

### 5. Docker `node_modules` permissions
After `npm install` in a container, fix ownership with `sudo chown -R $(whoami):$(whoami) frontend/node_modules`.

### 6. `docker-entrypoint.sh` executable bit
Run `chmod +x backend/docker-entrypoint.sh` before starting.

### 7. `docker-entrypoint.sh` ignores arguments
Use `--entrypoint ""` for one-off commands: `docker compose run --rm --entrypoint "" api alembic upgrade head`.

### 8. Vite proxy hostname in Docker
Use service name: `proxy: { '/api': { target: 'http://api:8000', changeOrigin: true } }`.

### 9. Alembic version without tables
If `drop_all` removed tables but `alembic_version` remains, run `DELETE FROM alembic_version;` then `alembic upgrade head`.

### 10. Duplicate route without guard
Keep only one route definition with the correct `meta` guards.

### 11. Path traversal in filename
Sanitize filenames with `os.path.basename` and `os.path.realpath` checks.

### 12. Race condition on stock
Use `SELECT FOR UPDATE` when decrementing stock.
