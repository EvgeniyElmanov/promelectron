---
name: deploy
description: Deploy to test or prod Kubernetes environment. Triggers GitHub Actions workflow via gh CLI — no local kubectl needed.
argument-hint: "<test|prod|all>"
disable-model-invocation: true
allowed-tools: Bash(gh workflow run *) Bash(gh run list *) Bash(gh run view *) Bash(gh run watch *)
---

# Deploy: $ARGUMENTS

Target environment: **$ARGUMENTS**

Деплой идёт через GitHub Actions; локальный `kubectl` не нужен. Исключение — аварийный откат (rollback) внизу, он требует `kubectl`/`helm`.

## Pre-flight

```bash
git log -1 --oneline
git status --short
```

Если есть незакоммиченные изменения — предупреди пользователя и спроси, нужно ли сначала закоммитить.

Перед деплоем зафиксируй текущую рабочую ревизию release, чтобы откат был точным:

```bash
export KUBECONFIG=~/.kube/pokutniy
helm history promelectron -n promelectron | tail -5
PREVIOUS_REVISION=<текущая ревизия до деплоя>
```

## Trigger deployment via GitHub Actions

### Test

```bash
gh workflow run deploy.yml -f environment=test
```

Then watch the run:

```bash
gh run list --workflow=deploy.yml --limit=3
gh run watch   # streams live output of the latest run
```

### Prod — confirm with user first

Before deploying to prod, ask: **"Задеплоить в production? (yes/no)"**

Only proceed after explicit confirmation.

```bash
gh workflow run deploy.yml -f environment=prod
gh run watch
```

## Post-deploy: E2E smoke test

После успешного деплоя запусти E2E smoke:

```bash
gh workflow run e2e.yml -f environment=$ARGUMENTS
gh run watch
```

Дождись финального статуса run (`completed`).

Smoke-сценарии:

1. Главная загружается
2. Каталог виден
3. Логин работает
4. Добавление в корзину работает
5. Checkout работает (до оплаты)

### E2E failed — rollback-политика

- **Test:** выполняй **автоматический rollback** на зафиксированную ревизию. Подтверждение пользователя не требуется, но уведоми его:

  ```bash
  helm rollback promelectron $PREVIOUS_REVISION -n promelectron
  kubectl rollout status deployment/promelectron -n promelectron
  ```

- **Prod:** **не откатывай автоматически**. Сообщи пользователю результаты smoke и причины падения, спроси явного одобрения на rollback. После одобрения — выполни rollback на зафиксированную ревизию.

После rollback дождись, пока старая версия развернётся, снова запусти минимальный smoke и отчитайся.

## Check deployment status

```bash
gh run list --workflow=deploy.yml --limit=5
gh run view <run-id> --log
```

## Rollback (emergency — requires kubectl access)

Помимо автоматического отката по failed E2E smoke в test, ручной откат используется только для критических проблем:

```bash
export KUBECONFIG=~/.kube/pokutniy
helm history promelectron -n promelectron | tail -5
helm rollback promelectron <previous_revision> -n promelectron
kubectl rollout status deployment/promelectron -n promelectron
```

- В **test** — откат без подтверждения, но с уведомлением пользователя.
- В **prod** — откат только после явного одобрения пользователя.

## Отчёт

Обнови `docs/journal/session-log.md`:

```markdown
## <YYYY-MM-DD> — Деплой в <environment>
- Commit: <hash>
- Status: <success|failed>
- E2E: <passed|failed>
```

Сообщи пользователю:

- Окружение
- Commit hash
- GitHub Actions run URL
- Результат E2E

## Правила

- NEVER деплоить в prod без подтверждения.
- Проверять `git status` перед деплоем.
- Всегда запускать E2E smoke после деплоя.
- **Test:** failed E2E smoke → автоматический rollback на зафиксированную предыдущую ревизию.
- **Prod:** failed E2E smoke → уведомить пользователя и ждать явного одобрения на rollback.
- Test → prod, никогда наоборот.
- Миграции запускаются автоматически как Helm pre-install/pre-upgrade hook.
- Image tag = git SHA; никогда `:latest` в деплоях.
