---
name: deploy-conventions
description: Deployment conventions for promelectron — Helm chart structure, Harbor registry, Kubernetes namespaces, GitHub Actions CI/CD, and rollback procedures.
when_to_use: Load when working on infra/, Helm chart, .github/workflows/, or deployment procedures.
user-invocable: false
paths:
  - "infra/**"
  - ".github/workflows/**"
---

# Deploy Conventions — Promelectron

## Environments

| Env | Namespace | Helm release | Domain |
|-----|-----------|--------------|--------|
| Test | `promelectron-test` | `promelectron-test` | `promelectron-test.aidrivencode.ru` |
| Prod | `promelectron` | `promelectron` | `promelectron.aidrivencode.ru` |

## Infrastructure
- Registry: `harbor.kubeadm.ru/promelectron/promelectron-api`
- Image tags: git SHA — **never `:latest` in Helm values for deployments**
- Kubeconfig: `/home/aleksandr/.kube/pokutniy`
- Helm chart: `./infra/helm/`
- imagePullSecret: `harborcred`
- Storage class: `ceph-block`
- TLS: cert-manager + `letsencrypt-production`
- Ingress class: `nginx`

## CI/CD (GitHub Actions)

- Auto-deploy to test on every push to `main` touching `backend/**`, `frontend/**`, or `infra/helm/**`
- Manual `workflow_dispatch` for test, prod, or all
- Prod deploy requires `environment: production` gate (manual approval in GitHub)
- **Path filter caveat**: changes to `.github/workflows/` alone do NOT trigger a deploy — use `gh workflow run deploy.yml -f environment=test` to test workflow fixes manually

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `HARBOR_USERNAME` | Harbor registry login |
| `HARBOR_PASSWORD` | Harbor registry password |
| `GPG_PRIVATE_KEY` | GPG secret key for SOPS decryption — **must be exported with `--export-secret-keys`**, not `--export` |
| `GPG_PASSPHRASE` | Passphrase for the GPG key (required if key has one) |

### GPG / SOPS Setup for CI

Secrets are SOPS-encrypted with GPG key `EFE7C254B3297D737D5D832B576EE7224B73177C`.

The CI workflow (`.github/workflows/deploy.yml`) uses an **isolated GNUPGHOME** (`mktemp -d`) per run to avoid interfering with the runner's system keyring. Key requirements:

- `gpg-agent.conf` must include `allow-preset-passphrase` — without it, `gpg-preset-passphrase` returns "Not supported"
- `gpg-agent.conf` must include `allow-loopback-pinentry` and `no-allow-external-cache`
- `gpg.conf` must include `no-tty` and `pinentry-mode loopback`
- Passphrase is cached in the agent via `gpg-preset-passphrase --preset $keygrip` before SOPS runs
- **Never write to `~/.gnupg/gpg.conf` on the runner** — it breaks interactive GPG tools (`pass`, etc.)

**To re-export the GPG key for CI** (if secret needs updating):
```bash
# On the runner or any machine that has the key
gpg --export-secret-keys --armor EFE7C254B3297D737D5D832B576EE7224B73177C
# Copy output → update GPG_PRIVATE_KEY GitHub secret
```

### Migration Job Behaviour

- Runs as Helm `pre-upgrade,pre-install` hook (`alembic upgrade head`)
- Named `promelectron-migrate-<revision>` — revision increments with each Helm release
- Delete policy: `before-hook-creation` — previous job is auto-deleted before next upgrade
- **If SOPS fails**, the hook runs with empty secrets → migration can't connect to DB → `BackoffLimitExceeded`. Fix SOPS first; next deploy will clean up the stuck job automatically.

## Deploy Commands

```bash
export KUBECONFIG=/home/aleksandr/.kube/pokutniy
IMAGE_TAG=$(git rev-parse --short HEAD)

# Test
helm upgrade --install promelectron-test ./infra/helm \
  -f infra/helm/stage/test/values.yaml \
  -f <(sops -d infra/helm/stage/test/secrets.yaml) \
  --set api.image=harbor.kubeadm.ru/promelectron/promelectron-api:$IMAGE_TAG \
  --namespace promelectron-test --create-namespace

# Prod
helm upgrade --install promelectron ./infra/helm \
  -f infra/helm/stage/prod/values.yaml \
  -f <(sops -d infra/helm/stage/prod/secrets.yaml) \
  --set api.image=harbor.kubeadm.ru/promelectron/promelectron-api:$IMAGE_TAG \
  --namespace promelectron --create-namespace
```

Migration runs automatically as a Helm pre-install/pre-upgrade hook (`alembic upgrade head`).

## Rollback
```bash
helm rollback promelectron -n promelectron        # Helm-level rollback
kubectl rollout undo deployment/promelectron-api -n promelectron  # Pod-level
```

## Rules
- Never deploy to prod without test verified first
- Never use `:latest` as image tag
- All K8s changes through Helm — no direct `kubectl apply` to prod
