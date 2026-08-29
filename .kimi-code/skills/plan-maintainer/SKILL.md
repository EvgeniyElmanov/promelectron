---
name: plan-maintainer
description: >
  Operational plan maintainer for Promelectron. Runs analyze/update/propose/sprint-review/improve
  commands against `.agent/PLANNING_HANDOFF.md` and `.agent/BACKLOG.md`.
  `improve` runs the continuous improvement loop: analyzes failure patterns across
  all pipeline runs (scripts/agent_improve.py) and proposes rule/skill updates.
  Use for concrete backlog operations, not strategic roadmap decisions.
type: prompt
whenToUse: When the user asks about project status, priorities, roadmap, sprint planning, what to do next, or recurring agent failure patterns, and detailed backlog operations are needed.
arguments: "<action: analyze|update|propose|sprint-review|improve>"
disableModelInvocation: false
---

# Plan Maintainer / Менеджер планов

Поддерживай `.agent/PLANNING_HANDOFF.md` и `.agent/BACKLOG.md` как единый источник истины для повседневной работы.

> Для стратегических решений по роадмапу используй `/skill:project-manager`.

## Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило.

---

## Ограничения API (Kimi K3)

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Ограничения модели и API (Kimi K3).

---

## Обязательный контекст

Перед анализом или редактированием прочитай:
1. `.agent/PLANNING_HANDOFF.md`
2. `.agent/BACKLOG.md`
3. `PROJECT_CONTEXT.md`
4. `.agent/BLOCKERS.md`
5. `.agent/SESSION_LOG.md`
6. [Rule: Agent Commons](../../rules/agent-commons.md)

---

## Команды

### `analyze`
Прочитай `.agent/PLANNING_HANDOFF.md` → `.agent/BACKLOG.md` → `git log --oneline -30` → просканируй ключевые файлы → сообщи о расхождениях.

### `update`
Прочитай `.agent/BACKLOG.md` → проверь конкретную задачу в коде → обнови статус → запиши обратно.

### `propose`
Прочитай `.agent/BACKLOG.md` → определи разблокированные P0/P1 → оцени capacity → напиши предложение по спринту.

### `sprint-review`
Прочитай `.agent/BACKLOG.md` → `git log --since="1 week ago"` → сравни запланированное и фактическое → напиши review.

### `improve`
Continuous improvement loop — анализ failure patterns поперёк всех задач пайплайна.

1. Запусти анализатор:
   ```bash
   python3 scripts/agent_improve.py            # или --last N для последних N задач
   ```
2. Прочитай отчёт. Для каждого паттерна:
   - **Покрыто правилами: нет — НОВОЕ** → предложи конкретный текст правила для указанного файла (rule-worthy) или правку скилла роли (skill-worthy). Применяй только с одобрения пользователя.
   - **Покрыто правилами: да** → правило существует, но не сработало. Проверь, почему: правило слишком общее? Не на том слою (ловит reviewer, а должен self-review developer'а)? Предложи усиление или перенос проверки на более ранний слой.
3. Итог — список «Предлагаемые улучшения пайплайна» с конкретными правками; doc-worthy разовые уроки допиши в `.kimi-code/LESSONS_LEARNED.md`.

Рекомендуемый ритм: в конце спринта (перед `sprint-review`) и после любой задачи с 2+ итерациями ревью.

---

## Чеклист анализа

Для каждой задачи проверь:
- [ ] **Code exists** — grep по именам функций/компонентов
- [ ] **Tests exist** — grep по `test_` + имя задачи
- [ ] **Routes registered** — проверь `main.py` или router includes
- [ ] **Frontend linked** — проверь views, router, API calls
- [ ] **Env vars set** — проверь `config.py`, `.env.example`, K8s manifests
- [ ] **CI covers it** — проверь `.github/workflows/`
- [ ] **Docs updated** — проверь `README.md`, `.kimi-code/skills/<role>/SKILL.md` и `.kimi-code/rules/`, если изменились агентские правила

Никогда не полагайся только на `ROADMAP.md` — он устаревает.

---

## Правила обновления

1. Evidence first — отмечай `[x]` только если можешь указать на commit или файл.
2. Link commits — при отметке done добавляй `(commit: abc1234)`.
3. Explain blocks — при отметке `[!]` объясни точный блокер.
4. Date everything — добавляй `(updated: YYYY-MM-DD)` к изменениям статуса.
5. Preserve history — не удаляй старые задачи; перемещай в "Completed".

---

## Формат предложения спринта

```markdown
## Sprint N — YYYY-MM-DD to YYYY-MM-DD

**Theme:** <one-line goal>
**Capacity:** <estimated hours or story points>

### P0 (Must)
- [ ] **ID-001** Title (M) — risk: medium

### P1 (Should)
- [ ] **ID-002** Title (S) — risk: low

### P2 (Could)
- [ ] **ID-003** Title (L) — risk: high

### Допущения
- ...

### Риски
- ...
```

---

## Anti-patterns

- ❌ Не создавай задачи длиннее 1 дня работы.
- ❌ Не назначай задачи в спринт без проверки зависимостей.
- ❌ Не скрывай блокеры — эскалируй их.
- ❌ Не дублируй задачи между PLANNING_HANDOFF.md и ROADMAP.md.
- ❌ Не удаляй выполненные задачи — архивируй их.
