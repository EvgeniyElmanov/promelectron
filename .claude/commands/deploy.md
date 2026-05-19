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
gh run watch
```

## For `prod` — confirm with user first

Before deploying to prod, ask: **"Are you sure you want to deploy to production?"**

Only proceed after explicit confirmation.

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
