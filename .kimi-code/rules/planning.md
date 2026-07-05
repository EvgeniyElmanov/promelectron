---
name: planning
description: >
  Rules for maintaining project plans, roadmaps, task prioritization, and the Definition of Done.
type: prompt
disableModelInvocation: true
---

# Rule: planning

> Правила ведения планов, приоритизации задач и Definition of Done для Promelectron.
> Follow [Rule: Agent Commons](agent-commons.md) > Language Rule.

## Single Source of Truth

`.agent/PLANNING_HANDOFF.md` — единственный авторитетный план. `ROADMAP.md` — историческая справка.

- При обновлении планов сначала редактируй `.agent/PLANNING_HANDOFF.md`.
- Если `ROADMAP.md` противоречит `.agent/PLANNING_HANDOFF.md`, побеждает `.agent/PLANNING_HANDOFF.md`.
- Обновляй `ROADMAP.md` только по явному запросу пользователя.

## Task Format

Задачи в `.agent/PLANNING_HANDOFF.md` и `.agent/BACKLOG.md` используют формат, совместимый с таблицей бэклога:

```markdown
| ID | Задача | Issue | Агент | Приоритет | Статус | Зависимости | Оценка | Блокер |
```

Где:
- **ID** — `#N`, `task-slug` или `ID-XXX`
- **Приоритет** — `P0` / `P1` / `P2` / `P3`
- **Статус** — `todo`, `in_progress`, `in_review`, `done`, `blocked`
- **Оценка** — дни/недели или `(S|M|L)`

Для подробного описания в `.agent/PLANNING_HANDOFF.md` допустим формат:

```markdown
- **ID-XXX** Task title (S|M|L) — risk: low|medium|high
  - **Why:** Обоснование
  - **What:** Конкретные результаты
  - **Depends on:** ID зависимых задач
  - **Acceptance:** Как проверить выполнение
```

## Status Definitions

| Статус | Значение | Применение |
|--------|----------|------------|
| `todo` | Не начато | В бэклоге, но не в работе |
| `in_progress` | В работе | Активная разработка |
| `in_review` | На ревью | PR открыт |
| `done` | Готово | Влито в `main`, проверено |
| `blocked` | Заблокировано | Есть внешний блокер |

## Prioritization Matrix

1. **P0 — Production blocker / Security risk** — ломает прод или уязвимость
2. **P1 — Regression / Feature blocker** — ломает существующее или блокирует другие задачи
3. **P2 — Business value** — напрямую влияет на пользователей/выручку
4. **P3 — Tech debt** — замедляет будущую разработку

## Sprint Boundaries

- Спринт = 2 недели (как в `.agent/BACKLOG.md`).
- В спринте не более 2 задач P0 и 3 задач P1.
- В конце спринта обнови `.agent/PLANNING_HANDOFF.md` и `.agent/BACKLOG.md`:
  - Что выполнено
  - Что не выполнено и почему
  - Новые блокеры
  - Предложение по следующему спринту

## Dependency Rules

- Не начинай задачу, пока её зависимости не в статусе `done`.
- Если зависимость `blocked` — эскалируй немедленно.
- Фиксируй кросс-командные зависимости (infra, design, 3rd party APIs).

## Assumption Tracking

Каждая оценка содержит допущения. Фиксируй их:

```markdown
**Assumptions:**
- MinIO уже развёрнут в K8s (подтверждено: да)
- `API_BASE_URL` добавит DevOps (owner: @devops)
- Schema changes не нужны
```

Если допущение оказывается неверным — переоценивай задачу немедленно.

## Definition of Done

Задача считается Done только когда:

- [ ] Код написан, протестирован и влит в `main`
- [ ] Тесты проходят: backend + frontend + E2E (если UI)
- [ ] Линтер и security-чеклист чисты
- [ ] Фича работает в local/dev окружении
- [ ] GitHub Issue закрыт, статус в GitHub Project board — Done
- [ ] `.agent/BACKLOG.md` / `.agent/SESSION_LOG.md` / `PROJECT_CONTEXT.md` обновлены
- [ ] `.agent/BLOCKERS.md` обновлён, если были блокеры
- [ ] Новые follow-up задачи созданы только с explicit approval пользователя

---
