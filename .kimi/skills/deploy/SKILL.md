---
name: deploy
description: >
  Deploy Promelectron to test or production Kubernetes environment.
  Triggers GitHub Actions workflow via gh CLI, watches deployment progress,
  runs E2E smoke tests, and reports status. Requires explicit user confirmation
  for production deployments. Triggers on: deploy, deployment, release, production,
  prod, staging, test, rollout, deploy, деплой, прод, стейджинг, production deploy.
argument-hint: "<test|prod>"
---

# /deploy — Deploy to Kubernetes

Деплой через GitHub Actions. Никакого локального `kubectl` не требуется.

---

## Pre-flight

Проверь состояние перед деплоем:

```bash
git log -1 --oneline
git status --short
```

**Если есть незакоммиченные изменения:**
Предупреди пользователя: **"Есть незакоммиченные изменения. Закоммитить перед деплоем?"**

---

## Trigger Deployment

### Test / Staging

```bash
gh workflow run deploy.yml -f environment=test
```

Затем следи за прогрессом:
```bash
gh run list --workflow=deploy.yml --limit=3
gh run watch   # live output последнего run
```

### Production

**Перед деплоем в prod — спроси подтверждение:**
> "Вы уверены, что хотите деплоить в production? (yes/no)"

Только после явного `yes`:
```bash
gh workflow run deploy.yml -f environment=prod
gh run watch
```

---

## Post-deploy: E2E Smoke Test

После успешного деплоя запусти E2E:

```bash
gh workflow run e2e.yml -f environment=<test|prod>
gh run watch
```

**Smoke test сценарии:**
1. Главная страница загружается
2. Каталог отображается
3. Login работает
4. Корзина (добавление товара)
5. Checkout (до оплаты)

Если E2E падает — сообщи пользователю и предложи откат.

---

## Check Deployment Status

```bash
# Список последних деплоев
gh run list --workflow=deploy.yml --limit=5

# Детали конкретного run
gh run view <run-id> --log
```

---

## Rollback (emergency)

Только при критических проблемах. Требует `kubectl`:

```bash
export KUBECONFIG=~/.kube/pokutniy
helm rollback promelectron -n promelectron
```

**Предупреди пользователя перед rollback.**

---

## Report

После деплоя сообщи:
```
🚀 Деплой завершён

**Окружение:** <test|prod>
**Git commit:** <hash>
**GitHub Actions run:** <url>
**E2E smoke test:** <passed|failed>

**Что развёрнуто:**
- <список изменений из последнего коммита>

**Следующие шаги:**
- Мониторинг: <Sentry url, если настроен>
- При проблемах: rollback через `helm rollback promelectron -n promelectron`
```

Обнови `.agent/SESSION_LOG.md`:
```markdown
## <YYYY-MM-DD> — Deploy to <environment>
- Commit: <hash>
- Status: <success|failed>
- E2E: <passed|failed>
```

---

## Rules

- **НИКОГДА** не деплой в prod без подтверждения
- Проверяй `git status` перед деплоем
- Всегда запускай E2E smoke после деплоя
- При падении E2E — эскалация пользователю, не скрывай
- Test → prod (никогда наоборот)
