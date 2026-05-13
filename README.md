# My Shop Backend

Интернет-магазин (маркетплейс) на FastAPI + Vue 3.

## Стек

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL 15
- **Frontend:** Vue 3 (Composition API), Vite, Vue Router, Axios
- **Тесты:** pytest (backend), Vitest (frontend), Playwright (e2e)
- **База данных:** PostgreSQL, миграции через Alembic
- **Инфраструктура:** Docker Compose, Makefile

## Быстрый старт

```bash
# 1. Клонировать и перейти в папку
# 2. Скопировать env

cp .env.example .env
# Отредактировать .env при необходимости

# 3. Запустить PostgreSQL
docker compose up -d postgres

# 4. Установить зависимости бэкенда
source venv/bin/activate
pip install -r requirements.txt

# 5. Применить миграции
make migrate

# 6. Заполнить тестовые данные (опционально)
make seed

# 7. Запустить dev-окружение
make dev
```

## Команды (Makefile)

```bash
make help           # Справка по командам
make dev            # Запуск backend + frontend
make stop           # Остановка dev-окружения
make test           # Все тесты
make test-backend   # pytest
make test-frontend  # Vitest
make test-e2e       # Playwright
make migrate        # Alembic upgrade head
make db-up          # PostgreSQL в Docker
```

## Структура проекта

```
/server/app/          — Бэкенд FastAPI
  api/                — REST эндпоинты
  models/             — SQLAlchemy ORM
  schemas/            — Pydantic схемы
  services/           — Бизнес-логика
/client/src/          — Фронтенд Vue 3
  views/              — Страницы
  components/         — Компоненты
  composables/        — Логика (useAuth и др.)
/tests/               — Backend тесты (pytest)
/client/src/__tests__/ — Frontend тесты (Vitest)
/e2e/                 — E2E тесты (Playwright)
/alembic/versions/    — Миграции БД
/scripts/             — Dev-скрипты
```

## API

Базовый URL: `http://localhost:8000/api/v1`

- `POST /register` — Регистрация
- `POST /login` — Логин
- `GET /products/` — Список товаров
- `GET /products/{id}` — Товар по ID
- `POST /cart/add` — Добавить в корзину
- `POST /orders/create` — Оформить заказ
- ... (полный список в документации)

## Документация API

При запущенном бэкенде:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
