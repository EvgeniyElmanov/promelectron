# CLAUDE.md — My Shop Backend

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
/server/app/          — Бэкенд FastAPI
  api/                — REST API эндпоинты
  models/             — SQLAlchemy ORM модели
  schemas/            — Pydantic схемы
  services/           — Бизнес-логика
  core/config.py      — Настройки (из env vars)
  db/database.py      — Async engine, session, get_db
  utils/auth.py       — JWT, хеширование, guard-зависимости
/client/src/          — Фронтенд Vue 3
  views/              — Страницы (Products, Login, Cart, Orders, Profile, Register, Admin, AuthCallback)
  components/         — Переиспользуемые компоненты (Header, ProductCard, BottomNav, SearchBar, CategoryChips, PromoBanner)
  composables/        — useAuth.js
  services/api.js     — Axios клиент
  router/index.js     — Vue Router
/tests/               — Бэкенд тесты (pytest)
/alembic/versions/    — Миграции БД
/e2e/                 — E2E тесты (Playwright)
/scripts/             — Dev-скрипты (run_dev.sh, stop_dev.sh)
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

## Команды запуска

```bash
# Dev-окружение (backend + frontend)
make dev
make stop

# Тесты
make test           # Все тесты
make test-backend   # pytest
make test-frontend  # vitest
make test-e2e       # playwright

# База данных
make migrate        # Alembic upgrade head
make seed           # Тестовые данные
make db-up          # PostgreSQL в Docker

# Отдельно
source venv/bin/activate && uvicorn server.app.main:app --reload --port 8000
cd client && npm run dev
```

## Правила разработки

1. **ТЕСТЫ ОБЯЗАТЕЛЬНЫ** — при написании нового функционала всегда создавай тесты:
   - Новый endpoint → `tests/test_<module>.py`
   - Новый Vue компонент → `client/src/__tests__/<Component>.spec.js`
   - Новая страница / критический flow → e2e через Playwright MCP
2. Type hints ВЕЗДЕ в Python
3. Composition API + `<script setup>` во Vue
4. Никаких `print()` — только `logging`
5. Обработка ошибок во всех API вызовах
6. Валидация через Pydantic (бэкенд)
7. Все I/O операции — async/await
8. Код на русском для UI, на английском для переменных/функций

## Агенты

- `backend-dev` — FastAPI + SQLAlchemy + pytest
- `frontend-dev` — Vue 3 + Vitest
- `tester` — e2e тесты через Playwright MCP
- `e2e-tester` — Playwright MCP E2E сценарии
- `integration-dev` — запуск dev-окружения
