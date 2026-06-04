# 🤖 AI Agent System — Promelectron

## Быстрый старт

```bash
# Вызвать агента на задачу
/implement "Добавить промокоды в корзину"

# Задеплоить
/deploy test

# Проверить код
/review

# Починить тесты
/fix-test
```

## Архитектура агентов

```
┌─────────────┐
│  Пользователь│
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /implement │────▶│  Architect  │────▶│   backend   │
│  (команда)  │     │  (spec.md)  │     │   /frontend │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                       ┌─────────────┐         │
                       │  code-review│◀────────┘
                       │ (findings)  │
                       └──────┬──────┘
                              │
                       ┌──────┴──────┐
                       │     QA      │
                       │(test-results)│
                       └──────┬──────┘
                              │
                       ┌──────┴──────┐
                       │  Merge PR   │
                       └─────────────┘
```

## Команды

### `/implement <описание> [--quick] [--backend-only] [--frontend-only]`

Полный цикл разработки фичи:
1. **Architect** — пишет `spec.md` (техническое задание)
2. **Git branch** — `feature/<task-id>`
3. **Developer** — пишет код (backend-dev / frontend-dev)
4. **Code Review** — проверка качества (max 3 итерации)
5. **QA** — прогон тестов (max 2 итерации)
6. **Merge Request** — `gh pr create`

**Флаги:**
- `--quick` — пропустить архитектурную фазу (для простых задач)
- `--backend-only` — только backend
- `--frontend-only` — только frontend

### `/deploy <test|prod>`

Деплой через GitHub Actions:
1. Проверяет git status
2. Запускает `gh workflow run deploy.yml`
3. Для prod — спрашивает подтверждение
4. После деплоя запускает E2E

### `/review`

Code review текущих изменений:
1. Читает `git diff`
2. Проверяет security (auth, SQL injection, PII)
3. Проверяет quality (type hints, tests, обработка ошибок)
4. Пишет `review/findings.md`

### `/fix-test`

Исправление падающих тестов:
1. Запускает все тесты
2. Анализирует ошибки
3. Чинит код или тесты
4. Перезапускает

### `/new-migration <описание>`

Создание Alembic миграции:
1. Проверяет модели
2. Генерирует миграцию
3. Проверяет `alembic upgrade head`

## Агенты

### `backend-dev`
**Зона:** `backend/src/app/`, `backend/tests/`
**Workflow:** model → schema → service → route → tests
**Before finish:** `pytest -x` + `ruff check`

### `frontend-dev`
**Зона:** `frontend/src/`
**Workflow:** component → API integration → test
**Before finish:** `npm test -- --run`

### `security-reviewer`
**Проверяет:**
- Missing auth checks
- SQL injection
- PII exposure
- Price manipulation
- Race conditions
**Классификация:** CRITICAL / HIGH / MEDIUM / LOW

### `code-reviewer`
**Проверяет:**
- Бизнес-логика не в route handlers
- Type hints
- Обработка ошибок
- Тесты на новый код
**Не редактирует код** — только пишет findings

### `tester` / `e2e-tester`
**Инструмент:** Playwright MCP
**Сценарии:**
- Главная: поиск, категории, карточки
- Регистрация → вход → заказ
- Корзина: добавление, удаление, оформление
- Профиль: редактирование, адрес
- Админ: пользователи, заказы, категории

### `qa`
**Запускает:** pytest + vitest + Playwright
**Проверяет:** Acceptance Criteria из spec.md
**Пишет:** `review/test-findings.md`

### `devops`
**Зона:** `infra/`, `.github/workflows/`
**Deploy:** Helm upgrade, kubectl, Docker
**Правило:** test → prod (никогда наоборот)

## Rules (правила конвенций)

| Rule | Описание | Пути |
|------|----------|------|
| `api.md` | Route handlers thin, business logic in services | `backend/src/app/api/**/*.py` |
| `models.md` | SQLAlchemy conventions | `backend/src/app/models/**/*.py` |
| `testing.md` | Test conventions | `backend/tests/**/*.py`, `frontend/src/__tests__/**/*.js` |
| `security.md` | Security checklist | Весь проект |
| `git.md` | Git workflow | `.git/` |

## MCP Integration

### Playwright MCP
Инструменты браузера для E2E:
- `browser_navigate` — открыть страницу
- `browser_click` — кликнуть
- `browser_type` — ввести текст
- `browser_snapshot` — посмотреть DOM
- `browser_take_screenshot` — скриншот

### Filesystem MCP
Доступ к файлам проекта без bash.

### Memory MCP
Сохраняет контекст между сессиями:
- Entities (фичи, баги, решения)
- Relations (зависимости)
- Observations (факты о проекте)

### Sequential Thinking MCP
Для сложных задач: разбивает на шаги, проверяет логику.

## Permissions (безопасность)

**Разрешено:**
- `make *`, `pytest *`, `alembic *`, `ruff *`
- `git status`, `git diff`, `git log`
- `npm *`, `npx *`
- `docker *`, `kubectl *`, `helm *`
- `gh workflow run *`, `gh run *`

**Запрещено:**
- `rm -rf *`
- `git push --force *`
- `git reset --hard *`
- `DROP *`, `truncate *`

## Hooks

### PostToolUse (Edit|Write)
```bash
cd backend && ruff check --fix --quiet "$CLAUDE_TOOL_INPUT_FILE" 2>/dev/null; true
```

Автоформатирование Python после каждого изменения.

## PROJECT_CONTEXT.md

В корне репозитория есть `PROJECT_CONTEXT.md` — единый «живой» источник контекста проекта.  
**Каждый агент читает его в начале сессии.** После значимых изменений агент дописывает вниз кратко: что изменилось и как теперь работает.

---

## Система агентов (обновлено 2026-06-02)

Проект использует файловую систему агентов в `.kimi/`:

| Файл | Назначение |
|------|-----------|
| `PROJECT_CONTEXT.md` | Единый источник контекста — стек, фичи, блокеры, API |
| `SESSION_START.md` | Шаблон входа в сессию (автовыбор роли + контекст) |
| `ROUTER.md` | Документация роутера |
| `scripts/kimi-task.sh` | Автоматический роутер задач |
| `.kimi/agents/*.md` | Инструкции для каждой роли |
| `.kimi/rules/*.md` | Правила: checklist, golden-path, dependency-map |
| `.agent/SESSION_LOG.md` | Append-only лог изменений |

---

## Workflow пример

### Задача: "Добавить промокоды"

```
Пользователь: /implement "Добавить промокоды в корзину"

1. Architect:
   - Читает код корзины и заказов
   - Пишет spec.md:
     * Model: PromoCode (code, discount_type, amount, limit, expires_at)
     * API: POST /cart/apply-promo, GET /admin/promo-codes
     * Frontend: поле в корзине
     * Tests: backend + frontend

2. Пользователь подтверждает spec

3. Git branch: feature/add-promo-codes

4. backend-dev:
   - Создаёт model PromoCode
   - Создаёт schema PromoCodeCreate, PromoCodeOut
   - Создаёт service PromoCodeService
   - Добавляет API endpoints
   - Пишет тесты test_promo_codes.py

5. frontend-dev:
   - Добавляет поле в Cart.vue
   - Добавляет API вызов applyPromo
   - Обновляет отображение итога
   - Пишет тесты Cart.spec.js

6. code-reviewer:
   - Проверяет код
   - Пишет findings.md
   - Если APPROVED → идём дальше
   - Если FIXES_NEEDED → чиним (max 3 итерации)

7. QA:
   - Запускает pytest, vitest, Playwright
   - Проверяет Acceptance Criteria
   - Пишет test-findings.md
   - Если TESTS_PASSED → идём дальше
   - Если TESTS_FAILED → чиним (max 2 итерации)

8. Merge Request:
   - git push origin feature/add-promo-codes
   - gh pr create --title "feat: promo codes" ...
   - Сообщает пользователю ссылку на PR
```

## Красные флаги (нельзя)

- ❌ Создать модель БД, но не создать миграцию
- ❌ Написать endpoint, но не написать тест
- ❌ Удалить старый компонент, а новый ещё не работает
- ❌ Закоммитить с `console.log`, `debugger`
- ✅ Push в main разрешён по явному запросу пользователя (обычно используем PR)
- ❌ Коммит без разрешения пользователя

## 🪤 Известные ловушки и ошибки (Promelectron)

> Реальные проблемы, которые уже случались. Проверять перед коммитом.

### 1. Тесты не должны трогать dev/prod БД
**Что случилось:** `conftest.py` использовал `DATABASE_URL` напрямую → `drop_all` в фикстуре снёс все таблицы dev-БД.
**Фикс:** Всегда использовать отдельную тестовую БД:
```python
# conftest.py
_env_url = os.getenv("DATABASE_URL", "")
if "postgresql" in _env_url:
    TEST_DATABASE_URL = _env_url.rsplit("/", 1)[0] + "/promelectron_test"
else:
    TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
```
**Проверка:** `docker exec postgres psql -U postgres -d promelectron -c "\dt"` — таблицы должны быть.

### 2. Rate limiting ломает тесты
**Что случилось:** `slowapi` блокировал тестовые запросы → `KeyError`, `429`.
**Фикс:** Сброс лимитера в `client` fixture:
```python
@pytest.fixture
async def client(test_session):
    from src.app.utils.rate_limiter import limiter
    limiter.reset()  # Очищаем счётчики перед каждым тестом
    ...
```

### 3. SQLite ≠ PostgreSQL
**Что случилось:** Тесты, написанные под SQLite, падали на PostgreSQL:
- `ForeignKeyViolationError` — SQLite игнорирует FK по умолчанию
- `UniqueViolationError` — SQLite не всегда проверяет unique
- `ProgrammingError` — различия в SQL синтаксисе
**Фикс:** Всегда запускать `make test-backend` (PostgreSQL в Docker), никогда `pytest` локально на SQLite.

### 4. Trailing slash в FastAPI
**Что случилось:** `api.get('/categories')` → 307 redirect → axios теряет заголовки/теряется в CORS.
**Фикс:** Всегда использовать trailing slash, как в декораторе:
```javascript
// Правильно
api.get('/categories/')   // @router.get("/")
api.post('/categories/')  // @router.post("/")
```

### 5. Docker node_modules permissions
**Что случилось:** `npm install` в контейнере (`node:20-alpine`, root) создаёт `node_modules` с `root:root` → хост не может писать.
**Фикс:** После работы с Docker:
```bash
sudo chown -R $(whoami):$(whoami) frontend/node_modules
```
**Или:** всегда ставить зависимости на хосте, а не в контейнере.

### 6. docker-entrypoint.sh executable bit
**Что случилось:** Volume mount перезаписывает файл из хоста → теряется `+x` → `permission denied` при старте.
**Фикс:** Проверять перед запуском:
```bash
chmod +x backend/docker-entrypoint.sh
```

### 7. docker-entrypoint.sh игнорирует аргументы
**Что случилось:** Entrypoint всегда запускает `seed_data.py + uvicorn`, `$@` не передаётся → `make migrate` не работает.
**Фикс (workaround):** В Makefile использовать `--entrypoint ""`:
```makefile
migrate:
	docker compose run --rm --entrypoint "" api alembic upgrade head
```

### 8. Vite proxy hostname в Docker
**Что случилось:** `target: 'http://127.0.0.1:8000'` в `vite.config.js` — frontend контейнер не может достучаться до `127.0.0.1` хоста.
**Фикс:** Использовать имя сервиса:
```javascript
proxy: { '/api': { target: 'http://api:8000', changeOrigin: true } }
```

### 9. Alembic version без таблиц
**Что случилось:** `drop_all` снёс таблицы, но `alembic_version` остался → `alembic upgrade head` считает, что всё на месте.
**Фикс:**
```sql
DELETE FROM alembic_version;
-- Затем
alembic upgrade head
```

### 10. Duplicate route без guard
**Что случилось:** Два `path: '/admin'` — первый без `meta: { requiresAdmin }` перехватывал все запросы.
**Фикс:** Только один маршрут с guard:
```javascript
// ❌ Неправильно
{ path: '/admin', component: Admin },
{ path: '/admin', component: Admin, meta: { requiresAuth: true, requiresAdmin: true } }

// ✅ Правильно
{ path: '/admin', component: Admin, meta: { requiresAuth: true, requiresAdmin: true } }
```

### 11. Path traversal в filename
**Что случилось:** `os.path.join(UPLOAD_DIR, str(product_id), filename)` с `filename=../../etc/passwd`.
**Фикс:** Санитизация:
```python
safe = os.path.basename(filename)
if not safe or safe.startswith("."):
    raise HTTPException(400, "Invalid filename")
real_fp = os.path.realpath(os.path.join(UPLOAD_DIR, str(product_id), safe))
real_base = os.path.realpath(os.path.join(UPLOAD_DIR, str(product_id)))
if not real_fp.startswith(real_base + os.sep):
    raise HTTPException(400, "Invalid filename")
```

### 12. Race condition на stock
**Что случилось:** `SELECT stock` → проверка → `UPDATE stock` в отдельных шагах → overselling при параллельных запросах.
**Фикс:** `SELECT FOR UPDATE`:
```python
product_result = await db.execute(
    select(Product).where(Product.id == ...).with_for_update()
)
```
