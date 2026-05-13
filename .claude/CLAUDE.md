# CLAUDE.md — My Shop Backend

## Проект

Интернет-магазин (E-commerce) с разделением на бэкенд и фронтенд.

## Стек

- **Backend:** Python 3.11+, FastAPI 0.104, SQLAlchemy 2.0 (async), PostgreSQL 15
- **Frontend:** Vue 3 (Composition API, `<script setup>`), Vite 8, Vue Router 5, Axios
- **Инфраструктура:** Docker, docker-compose
- **Тесты:** pytest (бэкенд), Vitest (фронтенд), Playwright (e2e)
- **Аутентификация:** JWT (access token) + OAuth2 (Google, Yandex)
- **Хеширование паролей:** Argon2 (passlib)

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
  components/         — Переиспользуемые компоненты (Header, ProductCard)
  composables/        — useAuth.js
  services/api.js     — Axios клиент
  router/index.js     — Vue Router
/tests/               — Бэкенд тесты (pytest)
/alembic/             — Миграции БД
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
- **Supplier** — name, description, api_key
- **Cart → CartItem** — корзина пользователя
- **Order → OrderItem** — заказы (статусы: pending, paid, shipped, delivered, cancelled)

## Команды запуска

```bash
# Бэкенд
source venv/bin/activate
uvicorn server.app.main:app --reload --port 8000

# Фронтенд
cd client && npm run dev          # http://localhost:5173

# Тесты бэкенда
pytest tests/ -v

# Тесты фронтенда
cd client && npx vitest run

# E2E тесты
bash scripts/run_e2e.sh

# Docker
docker-compose up -d
```

## Правила разработки

1. **ТЕСТЫ ОБЯЗАТЕЛЬНЫ** — при написании нового функционала всегда создавай тесты:
   - Новый endpoint → `tests/test_<module>.py`
   - Новый Vue компонент → `client/src/__tests__/<Component>.spec.js`
   - Новая бизнес-логика → unit тесты
2. Type hints ВЕЗДЕ в Python
3. Composition API + `<script setup>` во Vue
4. Никаких `print()` — только `logging`
5. Обработка ошибок во всех API вызовах
6. Валидация через Pydantic (бэкенд) и Zod (фронтенд, если будет)
7. Все I/O операции — async/await
8. Код на русском для UI, на английском для переменных/функций

## Агенты

- `backend-dev` — FastAPI + SQLAlchemy + pytest
- `frontend-dev` — Vue 3 + Vitest
- `tester` — e2e тесты через Playwright MCP (запускает бэкенд + фронтенд)