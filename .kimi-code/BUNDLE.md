# 🤖 AI Agent System — Bundled References

> Консолидированный реестр Kimi skills и общих правил для проекта Promelectron.  
> Этот файл нужен для того, чтобы индекс навыков/правил поддерживался в одном месте и не дублировался между `AGENTS.md`.

---

## Ролевые навыки

| Роль | Вызов | Файл |
|------|-------|------|
| `architect` | `/skill:architect` | `.kimi-code/skills/architect/SKILL.md` — обёртка → `.agents/agents/architect.md` |
| `backend-dev` | `/skill:backend-dev` | `.kimi-code/skills/backend-dev/SKILL.md` — обёртка → `.agents/agents/backend-dev.md` |
| `frontend-dev` | `/skill:frontend-dev` | `.kimi-code/skills/frontend-dev/SKILL.md` — обёртка → `.agents/agents/frontend-dev.md` |
| `code-reviewer` | `/skill:code-reviewer` | `.kimi-code/skills/code-reviewer/SKILL.md` — обёртка → `.agents/agents/code-reviewer.md` |
| `security-reviewer` | `/skill:security-reviewer` | `.kimi-code/skills/security-reviewer/SKILL.md` — обёртка → `.agents/agents/security-reviewer.md` |
| `e2e-tester` | `/skill:e2e-tester` | `.kimi-code/skills/e2e-tester/SKILL.md` — обёртка → `.agents/agents/e2e-tester.md` |
| `qa` | `/skill:qa` | `.kimi-code/skills/qa/SKILL.md` — обёртка → `.agents/agents/qa.md` |
| `devops` | `/skill:devops` | `.kimi-code/skills/devops/SKILL.md` — обёртка → `.agents/agents/devops.md` |
| `project-manager` | `/skill:project-manager` | `.kimi-code/skills/project-manager/SKILL.md` |
| `plan-maintainer` | `/skill:plan-maintainer` | `.kimi-code/skills/plan-maintainer/SKILL.md` |
| `integration-dev` | `/skill:integration-dev` | `.kimi-code/skills/integration-dev/SKILL.md` |
| `dispatcher` | `/skill:dispatcher` | `.kimi-code/skills/dispatcher/SKILL.md` |

## Workflow-навыки

| Навык | Файл |
|-------|------|
| `/implement` | `.kimi-code/skills/implement/SKILL.md` — обёртка → `.agents/skills/implement/SKILL.md` |
| `/fix` | `.kimi-code/skills/fix/SKILL.md` |
| `/review` | `.kimi-code/skills/review/SKILL.md` |
| `/deploy` | `.kimi-code/skills/deploy/SKILL.md` — обёртка → `.agents/skills/deploy/SKILL.md` |
| `/context-sync` | `.kimi-code/skills/context-sync/SKILL.md` |
| `/plan-maintainer` | `.kimi-code/skills/plan-maintainer/SKILL.md` |
| `/promelectron` | `.kimi-code/skills/promelectron/SKILL.md` |
| `/spec` | `.kimi-code/skills/spec/SKILL.md` |
| `/qa-gate` | `.kimi-code/skills/qa-gate/SKILL.md` |
| `/ship` | `.kimi-code/skills/ship/SKILL.md` — обёртка → `.agents/skills/ship/SKILL.md` |
| `/flow-fix` | `.kimi-code/skills/flow-fix/SKILL.md` |
| `/flow-implement` | `.kimi-code/skills/flow-implement/SKILL.md` |
| `/board` | `.kimi-code/skills/board/SKILL.md` — обёртка → `.agents/skills/board/SKILL.md` |
| `/sessions` | `.kimi-code/skills/sessions/SKILL.md` — обёртка → `.agents/skills/sessions/SKILL.md` |
| `/flow-review` | `.kimi-code/skills/flow-review/SKILL.md` |

## Общие правила

| Правило | Файл |
|---------|------|
| Agent commons (язык, retry, контекст) | `.kimi-code/rules/agent-commons.md` |
| Pre-edit checklist | `.kimi-code/rules/pre-edit-checklist.md` |
| Golden path | `.kimi-code/rules/golden-path.md` |
| Dependency map | `.kimi-code/rules/dependency-map.md` |
| Security | `.kimi-code/rules/security.md` |
| Prompt format | `.kimi-code/rules/prompt-format.md` |
| Task template | `.kimi-code/rules/task-template.md` |
| Planning & Definition of Done | `.kimi-code/rules/planning.md` |
| Known pitfalls | `.kimi-code/rules/known-pitfalls.md` |
| Business rules | `.kimi-code/rules/business.md` |
