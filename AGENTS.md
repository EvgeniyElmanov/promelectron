# 🤖 AI Agent System — My Shop

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
**Зона:** `server/app/`, `tests/`
**Workflow:** model → schema → service → route → tests
**Before finish:** `pytest -x` + `ruff check`

### `frontend-dev`
**Зона:** `client/src/`
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
| `api.md` | Route handlers thin, business logic in services | `server/app/api/**/*.py` |
| `models.md` | SQLAlchemy conventions | `server/app/models/**/*.py` |
| `testing.md` | Test conventions | `tests/**/*.py`, `client/src/__tests__/**/*.js` |
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
cd server && ruff check --fix --quiet "$CLAUDE_TOOL_INPUT_FILE" 2>/dev/null; true
```

Автоформатирование Python после каждого изменения.

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
- ❌ Push в main напрямую (только через PR)
- ❌ Коммит без разрешения пользователя
