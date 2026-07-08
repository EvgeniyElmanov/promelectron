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
Kimi K2.7-Code работает в обязательном thinking mode; `reasoning_content` должен сохраняться между multi-turn tool calls.
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
```bash
gh workflow run e2e.yml -f environment=<test|prod>
gh run watch
```

Smoke-сценарии:
1. Главная загружается
2. Каталог виден
3. Логин работает
4. Добавление в корзину работает
5. Checkout работает (до оплаты)

Если E2E падает — отчитайся и предложи rollback.

---

## Аварийный откат

Только для критических проблем. Требуется kubectl:
```bash
export KUBECONFIG=~/.kube/config
helm rollback promelectron -n promelectron
```

Предупреди пользователя перед rollback.

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
- Test → prod, никогда наоборот.
- Миграция запускается автоматически как Helm pre-install/pre-upgrade hook.
- Image tag = git SHA; никогда `:latest` в деплоях.
