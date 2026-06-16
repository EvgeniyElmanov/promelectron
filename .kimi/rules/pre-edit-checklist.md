# Pre-edit Checklist — перед каждым изменением кода

> **Правило:** Нельзя редактировать/создавать код, пока не отмечены ВСЕ пункты.
> Этот чеклист читается перед началом работы над задачей.
>
> Система агентов живёт в `.kimi-code/skills/` и `.kimi/agents/`.
> Права и хуки для pipeline настраиваются в `~/.kimi-code/config.toml` (см. `.kimi-code/config.example.toml`).

---

## Обязательные проверки

### 1. Тесты
- [ ] Есть ли тесты на этот модуль/компонент?
- [ ] Если нет — нужно написать ДО или ВМЕСТЕ с кодом
- [ ] Запустил ли я `pytest -x` / `npm test -- --run`? Зелёные?

### 2. Миграция БД
- [ ] Меняю ли я модель SQLAlchemy (`Column`, `relationship`, `Table`)?
- [ ] Если ДА — создать Alembic миграцию: `alembic revision --autogenerate -m "..."`
- [ ] Проверить: `alembic upgrade head` проходит?

### 3. API Contract
- [ ] Меняю ли я response/request schema?
- [ ] Если ДА — обновить frontend API layer (axios calls, types)
- [ ] Trailing slash в endpoint? (`/items/`, не `/items`)

### 4. Env vars
- [ ] Добавил ли я новые переменные окружения?
- [ ] Если ДА — добавить в `.env.example`
- [ ] Добавить в `backend/src/app/core/config.py`

### 5. Линтер
- [ ] Запустил `ruff check` (backend) / `npm run lint` (frontend)?
- [ ] Ошибок нет? Если есть — исправить ДО коммита

### 6. Golden Path
- [ ] Мои изменения затрагивают корзину, checkout, auth, оплату?
- [ ] Если ДА — проверить связанные сценарии из `golden-path.md`

### 7. Hardcoded values
- [ ] Нет ли хардкода секретов, URL, ID?
- [ ] Все конфигурабельные значения вынесены в env/settings?

---

## Backend-specific

- [ ] Бизнес-логика в service, не в route handler?
- [ ] Использую `async`/`await` для всех DB-операций?
- [ ] Добавил `selectinload` если нужно избежать N+1?
- [ ] Обработал `IntegrityError` / `ForeignKeyViolationError`?

## Frontend-specific

- [ ] Использую Composition API (`<script setup>`)?
- [ ] Добавил `data-testid` для E2E-селекторов?
- [ ] Обновил Pinia store если менялось состояние?
- [ ] Нет `console.log` / `debugger` в production-коде?

---

## После завершения (before report)

- [ ] `make test` проходит (backend + frontend)?
- [ ] `make lint` проходит?
- [ ] `.agent/SESSION_LOG.md` дописан?
- [ ] `BACKLOG.md` обновлён (если задача из спринта)?
