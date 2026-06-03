# CLAUDE.md — Promelectron Backend

## Проект

Интернет-магазин (E-commerce) с разделением на бэкенд и фронтенд.

## Стек

- **Backend:** Python 3.11+, FastAPI 0.104, SQLAlchemy 2.0 (async), PostgreSQL 15
- **Frontend:** Vue 3 (Composition API, `<script setup>`), Vite 8, Vue Router 5, Axios
- **Инфраструктура:** Docker, docker-compose, Makefile
- **Тесты:** pytest (бэкенд), Vitest (фронтенд), Playwright (e2e)
- **Аутентификация:** JWT (access token) + OAuth2 (Google, Yandex)
- **Хеширование паролей:** Argon2 (passlib)
- **Миграции БД:** Alembic

## MCP Серверы (`.mcp.json`)

| Сервер | Назначение | Инструменты |
|--------|-----------|-------------|
| `playwright` | E2E тестирование через браузер | `browser_navigate`, `browser_click`, `browser_type`, `browser_snapshot`, `browser_take_screenshot` |
| `filesystem` | Доступ к файловой системе проекта | `read_file`, `write_file`, `list_directory`, `search_files`, `get_file_info` |
| `memory` | Память / Knowledge Graph между сессиями | `create_entities`, `create_relations`, `add_observations`, `read_graph`, `search_nodes` |
| `sequential-thinking` | Последовательное мышление для сложных задач | `sequentialthinking` |

## Структура

```
/backend/             — Бэкенд (Python package: src)
  src/app/            — FastAPI приложение
    api/              — REST API эндпоинты
    models/           — SQLAlchemy ORM модели
    schemas/          — Pydantic схемы
    services/         — Бизнес-логика
    core/config.py    — Настройки (из env vars)
    db/database.py    — Async engine, session, get_db
    utils/auth.py     — JWT, хеширование, guard-зависимости
  tests/              — pytest тесты
  alembic/versions/   — Миграции БД
  Dockerfile          — Docker образ (контекст: backend/)
/frontend/            — Фронтенд Vue 3
  src/
    views/            — Страницы
    components/       — Компоненты
    composables/      — useAuth.js и др.
    services/api.js   — Axios клиент
    router/index.js   — Vue Router
  e2e/                — Playwright E2E тесты
  tests/agent/        — AI agent тесты
  Dockerfile          — Docker образ (контекст: frontend/)
  playwright.config.js
/infra/
  docker-compose.yml  — Локальный dev (API + PostgreSQL + Redis + Frontend)
  helm/               — Kubernetes Helm чарт
```

## API эндпоинты (префикс /api/v1)

| Группа | Эндпоинты | Аутентификация |
|--------|-----------|----------------|
| `/register`, `/login` | Регистрация и вход | Нет |
| `/auth/{google,yandex}/login` | OAuth URL | Нет |
| `/auth/{google,yandex}/callback` | OAuth callback | Нет |
| `/auth/profile` | Профиль пользователя | JWT |
| `/me`, `/profile` | Данные пользователя | JWT |
| `/admin` | Админ-доступ | Admin |
| `/supplier` | Поставщик-доступ | Supplier |
| `/products/` | CRUD товаров | Частично |
| `/categories/` | CRUD категорий | Admin (create) |
| `/cart/` | Корзина | JWT |
| `/orders/` | Заказы | JWT |

## Модели БД

- **User** — id, email, hashed_password, role (user/admin/supplier), is_active
- **SocialAccount** — user_id, provider, provider_id, access_token
- **Product** — name, description, price, stock, category_id, supplier_id
- **Category** — name, description, parent_id (иерархия)
- **Supplier** — user_id (FK → users), name, description, api_key
- **Cart → CartItem** — корзина пользователя
- **Order → OrderItem** — заказы (статусы: pending, paid, shipped, delivered, cancelled)

## Команды (через Makefile + docker compose)

Все команды запускаются через `make`. Не используй `docker run` напрямую или `venv activate`.

```bash
# Dev-окружение
make dev              # Весь стек: API + DB + Redis + Frontend
make dev-backend      # Только бэкенд
make dev-frontend     # Только фронтенд (Vue на :5173)
make stop             # Остановить всё
make logs             # Логи всех сервисов
make logs-api         # Логи только API

# Тесты
make test             # Все unit-тесты (pytest + vitest)
make test-backend     # pytest (автоматически стартует postgres/redis)
make test-frontend    # vitest
make test-e2e         # Playwright E2E (стартует весь стек)
make test-visual      # Playwright visual smoke

# База данных
make migrate          # alembic upgrade head
make migrate-down     # alembic downgrade -1
make migrate-generate MSG="add table"  # сгенерировать миграцию
make seed             # тестовые данные

# Линт / Форматирование
make lint             # ruff + eslint
make format           # ruff format + prettier

# Сборка образов
make build            # Пересобрать всё
```

**Порты:** API → `http://localhost:8000`, Frontend → `http://localhost:5173`

## Правила разработки

> ### 🚨 ЗАПРЕТ НА КОММИТЫ БЕЗ РАЗРЕШЕНИЯ ПОЛЬЗОВАТЕЛЯ
> **НИКОГДА** не выполняй `git commit`, `git push`, `git merge`, `git rebase` или любые другие мутации git-истории без **явного разрешения** пользователя. Даже если фича полностью готова и все тесты зелёные — спроси «Закоммитить?» и жди ответа. Это правило абсолютно и без исключений.

1. **ТЕСТЫ ОБЯЗАТЕЛЬНЫ** — при написании нового функционала всегда создавай тесты:
   - Новый endpoint → `tests/test_<module>.py`
   - Новый Vue компонент → `frontend/src/__tests__/<Component>.spec.js`
   - Новая страница / критический flow → e2e через Playwright
2. **ДВОЙНАЯ ПРОВЕРКА (автотесты + visual smoke)** — после каждой фичи:
   - `make test-e2e` — 19 автотестов (регрессия)
   - `make test-visual` — скриншоты всех ключевых страниц (`test-results/visual-smoke/`)
   - Эквивалентно «ручной проверке через браузер», но автоматизировано
2. Type hints ВЕЗДЕ в Python
3. Composition API + `<script setup>` во Vue
4. Никаких `print()` — только `logging`
5. Обработка ошибок во всех API вызовах
6. Валидация через Pydantic (бэкенд)
7. Все I/O операции — async/await
8. Код на русском для UI, на английском для переменных/функций

## Декомпозиция больших задач (Feature Slicing)

Большие фичи (например, «Личный кабинет», «Чат», «Уведомления») НЕЛЬЗЯ делать одним огромным коммитом. Разбивай на **вертикальные срезы** — маленькие законченные инкременты, каждый из которых оставляет проект рабочим и проходящим все тесты.

### Принципы

1. **Каждый срез — end-to-end.** Он включает минимум: модель/схему → API → сервис → тест backend → UI-компонент → тест frontend. Не оставляй «висячий» backend без frontend и наоборот.
2. **Зелёные тесты на каждом шаге.** Перед коммитом обязательно `make test`. Если тесты ломаются — задача не считается завершённой.
3. **Stub вместо половины фичи.** Если backend готов, а frontend ещё нет — сделай минимальный UI (хотя бы отображение JSON-данных или заглушку). Если frontend готов, а backend ещё нет — используй mock-данные в `api.js`, но НЕ оставляй сломанные API-вызовы.
4. **Feature toggle для скрытия незавершённого.** Если нужно влить код, но показывать пользователям рано — скрой UI через `v-if="false"` или флаг `isFeatureEnabled`, а не оставляй сломанную страницу.
5. **Миграции БД — отдельный первый шаг.** Создай миграцию Alembic и убедись, что `make migrate` проходит БЕЗ ошибок, прежде чем писать бизнес-логику.
6. **Не удаляй старый код, пока новый не заменил его полностью.** Дублируй, проверь, удали. Не оставляй проект в промежуточном состоянии.

### Шаблон разбиения (на примере «Редактирование профиля»)

| # | Срез | Что внутри | Тесты |
|---|------|-----------|-------|
| 1 | **Backend: API обновления профиля** | `PATCH /me`, схема `UserUpdate`, сервис, валидация уникальности email | `tests/test_auth.py::test_update_profile` |
| 2 | **Backend: смена пароля** | `PATCH /me/password`, проверка старого пароля, хеширование нового | `tests/test_auth.py::test_change_password` |
| 3 | **Frontend: UI профиля (только просмотр)** | Новый `Profile.vue` с аватаркой-заглушкой, сеткой данных, кнопкой выхода. Старый профиль пока живёт параллельно или заменяется полностью | `frontend/src/__tests__/Profile.spec.js` |
| 4 | **Frontend: режим редактирования** | Форма изменения имени/email, валидация, кнопка «Сохранить», вызов `PATCH /me` | Тесты в `Profile.spec.js` + e2e |
| 5 | **Frontend: смена пароля в профиле** | Отдельная секция/модалка со старым и новым паролем | `frontend/src/__tests__/ProfilePassword.spec.js` или e2e |
| 6 | **E2E: полный flow** | Регистрация → вход → редактирование профиля → смена пароля → повторный вход с новым паролем | `e2e/profile.spec.js` |

### Красные флаги (нельзя так делать)

- ❌ Создать модель БД, но не создать миграцию.
- ❌ Написать endpoint, но не написать тест backend.
- ❌ Сделать `router.push('/new-page')`, но страницу ещё не создать.
- ❌ Удалить старый компонент, а новый ещё не работает.
- ❌ Закоммитить с `console.log`, `debugger`, закомментированным кодом или `@pytest.mark.skip`.

## Агенты

- `dispatcher` — автопереключение ролей при каждой задаче (читает `.agent/DISPATCHER_PROMPT.md`)
- `backend-dev` — FastAPI + SQLAlchemy + pytest
- `frontend-dev` — Vue 3 + Vitest
- `e2e-tester` — Playwright E2E сценарии (нажимает кнопки в браузере как пользователь)
- `integration-dev` — запуск и диагностика dev-окружения
- `code-reviewer` — code review
- `security-reviewer` — security audit
- `project-manager` — планирование и приоритеты

## Правило: тестирование после каждой фичи (АВТОМАТИЧЕСКИ)

> ⚠️ Это правило применяется **АВТОМАТИЧЕСКИ** после КАЖДОЙ фичи. Пользователю не нужно просить — просто делай.

После завершения любого изменения (backend, frontend, модель БД, API, UI):

### Шаг 1. Запустить все автотесты
```bash
make test           # backend pytest
make test-frontend  # vitest
```
Если падают — сначала исправить, только потом идти дальше.

### Шаг 2. Проверить по TESTER_RULES.md (обязательно)
Прочитать `TESTER_RULES.md` и выполнить для текущей фичи:
- **Сценарий A** — регистрация + ключевое действие (happy path)
- **Сценарий B** — если фича связана с заказом/оплатой, проверить полный цикл
- **Все роли** — guest / user / supplier / admin (кто касается фичи)
- **Edge cases** — ошибка 401/403, пустое состояние, валидация форм
- **Связанные фичи** — проверить что ничего не сломалось

### Шаг 3. E2E через Playwright MCP (если есть браузер)
Если доступен Playwright MCP — запустить E2E тест:
```bash
make test-e2e
```
Или вызвать агента `e2e-tester` для прохождения сценария через браузер.

### Шаг 4. Ручная проверка (если нет E2E теста)
Если автоматизация не покрывает сценарий — запустить dev-сервер и вручную пройти:
1. Открыть http://localhost:5173
2. Выполнить полный сценарий от начала до конца
3. Нажать ВСЕ кнопки, проверить ВСЕ состояния
4. Проверить мобильную версию (DevTools → 375px)

### Шаг 5. Только после зелёных тестов
- [ ] Все backend тесты проходят
- [ ] Все frontend тесты проходят
- [ ] E2E / ручная проверка пройдена
- [ ] Не сломаны существующие фичи

**Только тогда** фича считается готовой. Сообщить пользователю результат проверки.

---

> **Почему это важно:** Баг "You are not registered as a supplier" произошёл потому что после фичи "Роль supplier при регистрации" не был проверен полный сценарий: регистрация → создание товара. Автотесты не поймали, потому что unit-тесты мокируют сервисы. E2E проверка поймала бы сразу.
