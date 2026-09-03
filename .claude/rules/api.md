---
description: FastAPI route handler conventions — as they actually are in this codebase.
paths:
  - "backend/src/app/api/**/*.py"
  - "backend/src/app/schemas/**/*.py"
---

# API Route Conventions

> Код лежит в `backend/src/app/api/`. Правило под `backend/app/**` не загрузится.

- Обработчики тонкие: провалидировать вход (это делает Pydantic), вызвать **один** метод
  сервиса, вернуть схему. Бизнес-логика — в `backend/src/app/services/`.
- **Обёртки ответов в проекте нет.** Эндпоинты возвращают Pydantic-схемы напрямую
  (`response_model=...`). Не выдумывай `app/core/responses.py` — такого модуля не существует.
- Доступ к БД — `db: AsyncSession = Depends(get_db)`, сессии руками не создаются.
- Авторизация — `Depends(get_current_user)` / `get_current_active_admin` /
  `get_current_active_supplier`. **Проверка владения ресурсом обязательна и в сервисе тоже:**
  админский эндпоинт, фильтрующий по `current_user.id`, молча ломается (см. `update_order_status`).
- Пагинация — параметрами `skip: int = 0, limit: int = 20`. Отдельного `PaginationParams` нет.
- Роутер тегируется для OpenAPI: `APIRouter(prefix="/products", tags=["products"])`.
- Ограничение частоты — декоратор `@conditional_limit` (`app/utils/rate_limiter.py`).
  Новый публичный или дорогой эндпоинт без него — заявка на злоупотребление.

## Trailing slash

В проекте **сосуществуют оба варианта** (69 путей со слэшем, 46 без) — это известный долг, а не
свобода выбора. Правило: **новый эндпоинт повторяет форму соседей внутри своего роутера.**
Смешение внутри одного ресурса даёт 307-редирект, на котором часть HTTP-клиентов теряет тело
запроса или заголовок `Authorization`.

Существующие пути **не переименовываются** без отдельной задачи: от них зависит фронтенд.
