---
name: deploy
description: >
  Deploy Promelectron to test or production Kubernetes environment.
  Triggers GitHub Actions workflow via gh CLI, watches deployment progress,
  runs E2E smoke tests, and reports status. Requires explicit user confirmation for production deployments.
type: flow
whenToUse: When the user explicitly asks to deploy, release, rollout, or deploy to test/production/staging. This skill is manual-only.
arguments: "<test|prod>"
---

# /skill:deploy — Deploy to Kubernetes

Deploy via GitHub Actions. No local `kubectl` required for normal deploys — the emergency rollback path below is the exception and needs `kubectl`/`helm`.

## Language

Follow [Rule: Agent Commons](.kimi-code/rules/agent-commons.md) > Language Rule / Языковое правило.
Kimi K2.7-Code runs in mandatory thinking mode; `reasoning_content` must be preserved across multi-turn tool calls.
User-facing answers, reports, and artifacts must match the user's language.

---

## Required context

Before any deploy, read:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. [Rule: Agent Commons](.kimi-code/rules/agent-commons.md)
6. [Rule: Security](.kimi-code/rules/security.md)

---

## Pre-flight

```bash
git log -1 --oneline
git status --short
```

If there are uncommitted changes, warn the user and ask whether to commit first.

---

## Trigger Deployment

### Test / Staging

```bash
gh workflow run deploy.yml -f environment=test
```

Then watch:
```bash
gh run list --workflow=deploy.yml --limit=3
gh run watch
```

### Production

Ask for explicit confirmation:
> "Deploy to production? (yes/no)"

Only after `yes`:
```bash
gh workflow run deploy.yml -f environment=prod
gh run watch
```

---

## Post-deploy: E2E Smoke Test

After successful deploy:
```bash
gh workflow run e2e.yml -f environment=<test|prod>
gh run watch
```

Smoke scenarios:
1. Homepage loads
2. Catalog visible
3. Login works
4. Cart add works
5. Checkout works (up to payment)

If E2E fails, report and suggest rollback.

---

## Rollback (emergency)

Only for critical issues. Requires kubectl:
```bash
export KUBECONFIG=~/.kube/config
helm rollback promelectron -n promelectron
```

Warn the user before rolling back.

---

## Report

Update `.agent/SESSION_LOG.md`:
```markdown
## <YYYY-MM-DD> — Deploy to <environment>
- Commit: <hash>
- Status: <success|failed>
- E2E: <passed|failed>
```

Report to the user:
- Environment
- Commit hash
- GitHub Actions run URL
- E2E result

---

## Rules

- NEVER deploy to prod without confirmation.
- Check `git status` before deploy.
- Always run E2E smoke after deploy.
- Test → prod, never the reverse.
- Migration runs automatically as a Helm pre-install/pre-upgrade hook.
- Image tag = git SHA; never `:latest` in deployments.
