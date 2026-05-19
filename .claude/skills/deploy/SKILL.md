---
name: deploy
description: Deploy to test or prod Kubernetes environment. Triggers GitHub Actions workflow via gh CLI — no local kubectl needed.
argument-hint: "<test|prod|all>"
disable-model-invocation: true
allowed-tools: Bash(gh workflow run *) Bash(gh run list *) Bash(gh run view *) Bash(gh run watch *)
---

# Deploy: $ARGUMENTS

Target environment: **$ARGUMENTS**

## Pre-flight

```!
git log -1 --oneline
git status --short
```

## Trigger deployment via GitHub Actions

```bash
gh workflow run deploy.yml -f environment=$ARGUMENTS
```

Then watch the run:
```bash
gh run list --workflow=deploy.yml --limit=3
gh run watch   # streams live output of the latest run
```

## For `prod` — confirm with user first

Before deploying to prod, ask: **"Are you sure you want to deploy to production?"**

Only proceed after explicit confirmation.

```bash
gh workflow run deploy.yml -f environment=prod
```

## After deploy — run E2E

```bash
gh workflow run e2e.yml -f environment=$ARGUMENTS
gh run watch
```

## Check deployment status

```bash
gh run list --workflow=deploy.yml --limit=5
gh run view <run-id> --log
```

## Rollback (emergency — requires kubectl access)

```bash
export KUBECONFIG=~/.kube/pokutniy
helm rollback promelectron -n promelectron
```
