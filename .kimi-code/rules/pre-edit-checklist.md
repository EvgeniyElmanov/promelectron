---
name: pre-edit-checklist
description: >
  Pre-edit checklist for Promelectron agents.
type: prompt
disableModelInvocation: true
---

## Rule: pre-edit-checklist

> **Правило:** Нельзя редактировать/создавать код, пока не отмечены ВСЕ пункты.
> Этот чеклист читается перед началом работы над задачей.
>
> Система агентов живёт в `.kimi-code/`.
> Права и хуки для pipeline настраиваются в `~/.kimi-code/config.toml` (см. `.kimi-code/config.example.toml`).
> Режим `default_permission_mode = "manual"` — безопасный default. Режим `auto` разрешает read-only операции автоматически, но правки кода и shell-команды всё равно требуют approval. Режим `yolo` допустим только для коротких локальных экспериментов.

### Обязательный контекст (прочитать перед задачей)

- [ ] `PROJECT_CONTEXT.md`
- [ ] `.agent/BACKLOG.md`
- [ ] `.agent/BLOCKERS.md`
- [ ] `.agent/SESSION_LOG.md`
- [ ] Релевантный role skill из `.kimi-code/skills/<role>/SKILL.md`
- [ ] [Rule: Agent Commons](agent-commons.md) — язык, retry policy, API constraints Kimi K2.7-Code
- [ ] [Rule: Security](security.md) — всегда; lightweight pass для любой задачи, extended для auth/payments/PII/uploads/orders/webhooks

### Обязательные проверки

#### 1. GitHub Issue / Backlog
- [ ] Задача связана с GitHub Issue (новая или существующая)?
- [ ] Статус в `.agent/BACKLOG.md` / GitHub Project board обновлён?

#### 2. Тесты
- [ ] Есть ли тесты на этот модуль/компонент?
- [ ] Если нет — нужно написать ДО или ВМЕСТЕ с кодом
- [ ] Запустил ли я `make test-backend` / `make test-frontend`? Зелёные?

#### 3. Миграция БД
- [ ] Меняю ли я модель SQLAlchemy (`Column`, `relationship`, `Table`)?
- [ ] Если ДА — создать Alembic миграцию: `alembic revision --autogenerate -m "..."`
- [ ] Проверить: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head`

#### 4. API Contract
- [ ] Меняю ли я response/request schema?
- [ ] Если ДА — обновить frontend API layer (`frontend/src/api/`, composables)
- [ ] Trailing slash в endpoint? (`/items/`, не `/items`)

#### 5. Env vars
- [ ] Добавил ли я новые переменные окружения?
- [ ] Если ДА — добавить в `.env.example`
- [ ] Добавить в `backend/src/app/core/config.py`

#### 6. Линтер
- [ ] Запустил `make lint-backend` / `make lint-frontend`?
- [ ] Ошибок нет? Если есть — исправить ДО коммита

#### 7. Golden Path
- [ ] Мои изменения затрагивают корзину, checkout, auth, оплату?
- [ ] Если ДА — проверить связанные сценарии из [Rule: golden-path](golden-path.md)

#### 8. Hardcoded values
- [ ] Нет ли хардкода секретов, URL, ID?
- [ ] Все конфигурабельные значения вынесены в env/settings?

### Security — обязательно для ВСЕХ задач

Прочитай [Rule: Security](security.md) перед редактированием кода **всегда**, а не только для auth/payments/PII/uploads.

#### Lightweight pass (каждая задача)

- [ ] Auth guard на новых endpoint'ах?
- [ ] Проверка владения объектом (object-level permissions)?
- [ ] Валидация входных данных на границе API?
- [ ] Нет raw SQL с f-strings / string formatting?
- [ ] Нет хардкода секретов в коде/тестах?
- [ ] Нет PII/tokens в логах?
- [ ] Цены/скидки считаются на сервере?

#### Extended pass (auth/payments/PII/uploads/orders/webhooks)

Если задача затрагивает чувствительные зоны — пройди полный чеклист из [Rule: Security](security.md) (API endpoints, БД, бизнес-логика, фронтенд, логирование, project-specific риски, DevOps) и запусти `security-reviewer` после code review.

### Backend-specific

- [ ] Бизнес-логика в service, не в route handler?
- [ ] Использую `async`/`await` для всех DB-операций?
- [ ] Добавил `selectinload` если нужно избежать N+1?
- [ ] Обработал `IntegrityError` / `ForeignKeyViolationError`?
- [ ] Использую транзакции / rollback при ошибках?
- [ ] Endpoint идемпотентен, если это критично (payments, создание заказа)?

### Frontend-specific

- [ ] Использую Composition API (`<script setup>`)?
- [ ] Добавил `data-testid` для E2E-селекторов?
- [ ] Обновил composable, если менялось состояние (`useCart`, `useAuth`, и т.д.)?
- [ ] Нет `console.log` / `debugger` / `console.error` в production-коде?
- [ ] API-ключи/tokens только через `import.meta.env.VITE_*`, без хардкода?
- [ ] `v-html` используется только с доверенным HTML?

### После завершения (before report)

- [ ] `make pre-push` проходит (lint + unit + E2E)?
- [ ] `.agent/SESSION_LOG.md` дописан?
- [ ] `.agent/BACKLOG.md` обновлён (если задача из спринта)?
- [ ] `.agent/BLOCKERS.md` обновлён, если появился новый блокер?
- [ ] `PROJECT_CONTEXT.md` обновлён, если изменилась архитектура/API?

---
