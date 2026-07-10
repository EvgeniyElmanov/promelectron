---
name: plan-maintainer
description: >
  Operational plan maintainer for Promelectron. Runs analyze/update/propose/sprint-review
  commands against `.agent/PLANNING_HANDOFF.md` and `.agent/BACKLOG.md`.
  Use for concrete backlog operations, not strategic roadmap decisions.
type: prompt
whenToUse: When the user asks about project status, priorities, roadmap, sprint planning, or what to do next, and detailed backlog operations are needed.
arguments: "<action: analyze|update|propose|sprint-review>"
disableModelInvocation: false
---

# Plan Maintainer / Менеджер планов

Поддерживай `.agent/PLANNING_HANDOFF.md` и `.agent/BACKLOG.md` как единый источник истины для повседневной работы.

> Для стратегических решений по роадмапу используй `/skill:project-manager`.

## Язык

Следуй [Rule: Agent Commons](../../rules/agent-commons.md) > Language Rule / Языковое правило.

---

## Ограничения API (Kimi K2.7-Code)

- Thinking mode обязателен (`thinking={"type":"enabled"}`); `reasoning_content` должен сохраняться между multi-turn tool calls.
- Не считай переключение языка внутреннего рассуждения ошибкой. Пользовательские ответы, отчёты и артефакты должны соответствовать языку пользователя.
- `tool_choice` может быть только `"auto"` или `"none"`.
- Sampling-параметры фиксированы: `temperature=1.0`, `top_p=0.95`, `n=1`, `presence_penalty=0.0`, `frequency_penalty=0.0`.
- Контекстное окно 256K; при анализе больших бэклогов суммируй и читай только релевантные секции.

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
