---
name: task-template
description: >
  Template for the per-task coordination file `.agent/runs/<task-id>/task.md`.
type: prompt
disableModelInvocation: true
---

> Это reference-шаблон для `.agent/runs/<task-id>/task.md` (task-id — kebab-case).  
> Пайплайн создаёт этот файл автоматически; агенты читают его в начале задачи.
> См. [Rule: Agent Commons](agent-commons.md) > Языковое правило.

```yaml
---
task-id: <kebab-case-slug>
github_issue: #N
status: todo | in_progress | in_review | done
branch: feature/<task-id>
worktree: /abs/path/to/.worktrees/<task-id>
date: YYYY-MM-DD
flags: --quick | --backend-only | --frontend-only | --serial | --qa
estimated_tokens: 0
security_review: yes | no
---
```

## ЯЗЫК / LANGUAGE

Пользователь общается на русском. Все артефакты (spec, findings, отчёты, SESSION_LOG) — на русском. Код, команды, идентификаторы, пути и технические термины — в оригинале.

## ЗАДАЧА

[Краткое название, 3-7 слов]

## ОПИСАНИЕ

[Полное описание задачи]

## КОНТЕКСТ

- Что уже сделано:
- Где в коде смотреть (файлы, компоненты, таблицы):
- Связанные задачи / фичи:
- Текущий статус проекта по этой фиче:

## ЦЕЛЬ

[Что должно работать после выполнения. Одно конкретное предложение.]

## MUST-HAVES

- [ ] Конкретный обязательный результат 1
- [ ] Конкретный обязательный результат 2

## ACCEPTANCE CRITERIA

- [ ] Критерий приёмки 1
- [ ] Критерий приёмки 2

## OUT OF SCOPE

- [ ] Что явно НЕ делаем в этой задаче

## ОГРАНИЧЕНИЯ

- [ ] Не трогать: ...
- [ ] Не менять архитектурные решения без согласования
- [ ] Не удалять старый код, пока новый не работает
- [ ] Не добавлять новые зависимости без обоснования

## ОБЯЗАТЕЛЬНЫЙ КОНТЕКСТ (прочитать)

- [ ] `PROJECT_CONTEXT.md`
- [ ] `.agent/BACKLOG.md`
- [ ] `.agent/BLOCKERS.md`
- [ ] `.agent/SESSION_LOG.md`
- [ ] `.kimi-code/skills/<role>/SKILL.md`
- [ ] [Rule: Pre-edit Checklist](pre-edit-checklist.md)
- [ ] [Rule: Agent Commons](agent-commons.md)
- [ ] [Rule: Security](security.md) — всегда; lightweight pass для любой задачи, extended для auth/payments/PII/uploads/orders/webhooks

## КОНТЕКСТНЫЙ ПАКЕТ (для рабочего агента)

### Для backend-dev:
- [ ] API контракт (request/response schema)
- [ ] Модели БД, которые затрагиваются
- [ ] Сервисы, куда вставлять бизнес-логику
- [ ] Alembic миграция — нужна ли?

### Для frontend-dev:
- [ ] Ссылка на компонент-родитель (где вставлять)
- [ ] API контракт (какие поля приходят с бэка)
- [ ] Composable — создавать новый или использовать существующий?
- [ ] Дизайн-референс (скриншот / описание / макет)
- [ ] `data-testid` для E2E — добавить?

### Для devops:
- [ ] Helm values, которые меняются
- [ ] Env vars — добавить в `.env.example`, K8s manifests?
- [ ] CI/CD pipeline — затрагивается?

### Для e2e-tester:
- [ ] Тест-кейс: шаги → ожидаемый результат
- [ ] Селекторы / `data-testid`, которые нужны
- [ ] URL, на котором проверять

## ПРОВЕРКА (Definition of Done)

- [ ] `make test-backend` / `make test-frontend` проходят
- [ ] `make lint` не ругается
- [ ] `make pre-push` проходит (lint + unit + E2E)
- [ ] Ручная проверка: `curl ...` или скриншот UI
- [ ] E2E тест проходит (если затрагивает пользовательский сценарий)
- [ ] Документация обновлена (если API меняется)
- [ ] `.env.example` обновлён (если новые env vars)

## ОТЧЁТ ПО ЗАВЕРШЕНИЮ

Агент должен сообщить:
1. **Список изменённых файлов** (с путями)
2. **Результат проверки** (тесты, линтер, ручная проверка)
3. **Риски / технический долг** (если оставили)
4. **Блокеры** (если что-то мешает двигаться дальше)

## PR / MERGE

- PR URL:
- Review status: APPROVED / FIXES_NEEDED
- Merge approved by user: yes / no

---
