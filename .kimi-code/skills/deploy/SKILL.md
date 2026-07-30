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

# /skill:deploy — Деплой в Kubernetes

Деплой через GitHub Actions. Для обычных деплоев не нужен локальный `kubectl` — emergency rollback ниже является исключением и требует `kubectl`/`helm`.

## Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило.
Kimi K3 работает в обязательном thinking mode (отключить нельзя; глубина задаётся `reasoning_effort`); в multi-turn tool calls возвращай полное assistant message unchanged, включая `reasoning_content`.
Пользовательские ответы, отчёты и артефакты должны соответствовать языку пользователя.

---

## Обязательный контекст

Перед любым деплоем прочитай:
1. `PROJECT_CONTEXT.md`
2. `.agent/BACKLOG.md`
3. `.agent/BLOCKERS.md`
4. `.agent/SESSION_LOG.md`
5. [Rule: Agent Commons](../../rules/agent-commons.md)
6. [Rule: Security](../../rules/security.md)

---

## Предполётная проверка

```bash
git log -1 --oneline
git status --short
```

Если есть незакоммиченные изменения — предупреди пользователя и спроси, нужно ли сначала закоммитить.

---

## Запуск деплоя

### Test / Staging

```bash
gh workflow run deploy.yml -f environment=test
```

Затем наблюдай:
```bash
gh run list --workflow=deploy.yml --limit=3
gh run watch
```

### Продакшн

Запроси явное подтверждение:
> "Задеплоить в production? (yes/no)"

Только после `yes`:
```bash
gh workflow run deploy.yml -f environment=prod
gh run watch
```

---

## Post-deploy: E2E Smoke Test

После успешного деплоя:

1. Зафиксируй текущую рабочую ревизию release, чтобы откат был точным:
   ```bash
   helm history promelectron -n promelectron | tail -5
   PREVIOUS_REVISION=<revision до деплоя>
   ```
2. Запусти E2E smoke:
   ```bash
   gh workflow run e2e.yml -f environment=<test|prod>
   gh run watch
   ```
   Дождись финального статуса run (`completed`).

Smoke-сценарии:
1. Главная загружается
2. Каталог виден
3. Логин работает
4. Добавление в корзину работает
5. Checkout работает (до оплаты)

### E2E failed

```bash
python3 scripts/agent_state.py trace deploy <task-id-or-deploy-event> deploy_smoke_failed --actor orchestrator --data '{"environment": "test|prod", "run_url": "..."}'
```

- **Test / Staging:** выполняй **автоматический rollback** на зафиксированную ревизию. Подтверждение пользователя не требуется, но уведоми его:
  ```bash
  helm rollback promelectron $PREVIOUS_REVISION -n promelectron
  kubectl rollout status deployment/promelectron -n promelectron
  python3 scripts/agent_state.py trace deploy <...> deploy_rollback --actor orchestrator --data '{"environment": "test", "reason": "E2E smoke failed", "revision": $PREVIOUS_REVISION}'
  ```
- **Продакшн:** **не откатывай автоматически**. Сообщи пользователю результаты smoke, причины падения и спроси явного одобрения на rollback. После одобрения — выполни rollback с фиксацией ревизии и trace `deploy_rollback`.

После rollback снова запусти минимальный smoke (или дождись, пока старая версия развернётся) и отчитайся.

---

## Аварийный откат

Кроме автоматического отката по failed E2E smoke в test, ручной откат используется только для критических проблем. Требуется kubectl:

```bash
export KUBECONFIG=~/.kube/config
helm history promelectron -n promelectron | tail -5
helm rollback promelectron <previous_revision> -n promelectron
kubectl rollout status deployment/promelectron -n promelectron
```

- В **test** — откат без подтверждения, но с уведомлением пользователя.
- В **prod** — откат только после явного одобрения пользователя.

Всегда логируй trace: `python3 scripts/agent_state.py trace deploy <event-id> deploy_rollback --actor orchestrator --data '{"environment": "...", "reason": "...", "revision": ...}'`.

---

## Отчёт

Обнови `.agent/SESSION_LOG.md`:
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

---

## Правила

- NEVER деплоить в prod без подтверждения.
- Проверять `git status` перед деплоем.
- Всегда запускать E2E smoke после деплоя.
- **Test:** failed E2E smoke → автоматический rollback на зафиксированную предыдущую ревизию.
- **Prod:** failed E2E smoke → уведомить пользователя и ждать явного одобрения на rollback.
- Test → prod, никогда наоборот.
- Миграция запускается автоматически как Helm pre-install/pre-upgrade hook.
- Image tag = git SHA; никогда `:latest` в деплоях.
