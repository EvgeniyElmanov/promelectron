---
description: SQLAlchemy model and Alembic migration conventions — as they actually are in this codebase.
paths:
  - "backend/src/app/models/**/*.py"
  - "backend/src/app/db/**/*.py"
  - "backend/alembic/**/*.py"
---

# Database Model Conventions

> Пути важны: код живёт в `backend/src/app/`, а миграции — в `backend/alembic/versions/`.
> Правило, написанное под `backend/app/**`, не загрузится вообще.

## Как здесь на самом деле

- Все модели наследуются от `Base` из **`backend/src/app/db/database.py`** (`DeclarativeBase`).
- **Первичные ключи целочисленные:** `id = Column(Integer, primary_key=True, index=True)`.
  UUID для PK в этом проекте не используются.
- **Все таблицы в схеме `public`.** Декомпозиции на PG-схемы нет; `__table_args__` со `schema`
  не ставится.
- **Деньги — `Numeric(10, 2)`**, не `Float` и не целые копейки. `Product.price` мигрирован
  во `Numeric` (`8965b510122d`), актуальная цена вынесена в `product_prices`
  (`models/product_price.py`) и подтягивается через `column_property`.
  Оставшийся `Float` — `delivery_method.base_price`, это долг, а не образец.
- Внешние ключи обычные, `ForeignKey(...)` между таблицами разрешён.
- Идентификаторы из 1С хранятся отдельным полем `onec_id` (`String(36)`, unique, index) —
  не подменяют собой PK.

## Миграции

- Генерация: `make migrate-generate MSG="описание"`. Применение: `make migrate`.
- **`make migrate-check` (`alembic check`) должен быть зелёным.** С issue #185 это гейт в
  `deploy.yml`: расхождение модели и схемы красит выкат. Проверяй локально до PR.
- Сгенерированную миграцию читай глазами: автогенерация регулярно тащит лишнее и роняет
  нужное. Особенно — индексы и типы `Numeric`.
- Уже применённые миграции не редактируются — расхождение чинится новой миграцией.
- Дрифт «модель без миграции» чинится **возвратом колонки в модель**, если миграция уже в
  цепочке (так закрывали #183), а не новой миграцией поверх.

## Индексы

Индексы есть на `id` и на onec/cdek-полях. **Горячие внешние ключи не проиндексированы** —
`orders.user_id`, `order_items.order_id`, `carts.user_id`, `cart_items.cart_id`,
`reviews.product_id`, `products.category_id`, `products.supplier_id`. Добавляя модель или
запрос по FK, ставь индекс сразу и не воспроизводи этот долг.
