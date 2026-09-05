---
name: task-template
description: >
  Template for the per-task coordination file `.agent/runs/<task-id>/task.md`.
type: prompt
disableModelInvocation: true
---

> Это reference-шаблон для `.agent/runs/<task-id>/task.md` (task-id — kebab-case).  
> Пайплайн создаёт этот файл автоматически (`implement-pipeline.py setup`); агенты читают его в начале задачи.  
> См. [Rule: Agent Commons](agent-commons.md) > Языковое правило.

Канонический формат заголовка — markdown-заголовки (не YAML): именно его пишет генератор
и парсит `agent_metrics._parse_task_md`. Дальше агент может дополнять файл секциями ниже по необходимости.

```markdown
# Task: <task-id>

## Description
<полное описание задачи>

## Flags
<активные флаги или "none">

## Date
<YYYY-MM-DD>

## GitHub
- github_issue: #N
- issue_url: https://...
```

Секция `## GitHub` добавляется автоматически при `create-issue` (`github_issue` обязателен для `set-status`).
Опциональные поля, которые можно добавить в `## Description` или отдельными секциями: `jira_issue`,
`confluence_spec_url`, `figma_file_key`, `security_review`, `estimated_tokens`.

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
- [ ] `docs/backlog.md`
- [ ] `docs/blockers.md`
- [ ] `docs/journal/session-log.md`
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
