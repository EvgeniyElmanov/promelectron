---
name: golden-path
description: >
  Golden path scenarios for Promelectron.
type: prompt
disableModelInvocation: true
---

## Rule: golden-path

> **Правило:** Если твои изменения затрагивают модуль из списка ниже — перед финишем проверь сценарий.
> Проверяй только в dev/test окружении, никогда против production.
> Не обязательно писать тест, достаточно ручной проверки (curl / UI / Playwright).
>
> См. [Rule: Agent Commons](agent-commons.md) > Языковое правило.

### Сценарий 1: Полный путь покупки (авторизованный)

```
Регистрация → Логин → Каталог → Карточка товара → Корзина → Checkout → Оплата → Успех
```

**Затрагиваемые модули:** `auth`, `products`, `cart`, `orders`, `payments`, `notifications`  
**Проверка:**
1. `POST /api/v1/register/` → 201
2. `POST /api/v1/login/` → JWT токен
3. `GET /api/v1/products/` → список товаров
4. `POST /api/v1/cart/add` → добавить в корзину
5. `POST /api/v1/orders/create/` → создать заказ
6. `POST /api/v1/payments/{order_id}/` → создать платёж (confirmation_url)
7. `GET /api/v1/orders/{id}/` → статус "paid" после webhook или `POST /api/v1/payments/{order_id}/mock-confirm/` в dev-режиме
8. WebSocket уведомление пришло

### Сценарий 2: Полный путь покупки (гость)

```
Каталог (гость) → Корзина (localStorage) → Checkout → Login → Merge корзины → Оплата
```

**Затрагиваемые модули:** `products`, `guest-cart`, `cart`, `auth`, `orders`, `payments`  
**Проверка:**
1. Гость добавляет товар (localStorage)
2. Гость идёт в checkout → redirect на `/login`
3. После login `POST /api/v1/cart/merge` → корзина объединена
4. `POST /api/v1/orders/create/` → заказ создан
5. `POST /api/v1/payments/{order_id}/` → платёж создан

### Сценарий 3: OAuth вход

```
Yandex/Google OAuth → Callback → Авторизация → Профиль
```

**Затрагиваемые модули:** `auth/yandex`, `auth/google`, `users`  
**Проверка:**
1. `GET /api/v1/auth/{provider}/login` → redirect
2. Callback → `GET /api/v1/auth/callback?code=...&state=...` → JWT + user
3. `GET /api/v1/me/` → профиль загружен

### Сценарий 4: Поставщик / админ — CRUD товара

```
Админ/поставщик логин → CRUD товара → Товар виден в каталоге
```

**Затрагиваемые модули:** `auth`, `admin/products`, `products`, `supplier`  
**Проверка:**
1. Admin/supplier login → `POST /api/v1/login/`
2. `POST /api/v1/products/` → товар создан (supplier)
3. `GET /api/v1/products/` → новый товар в списке
4. `GET /api/v1/products/{id}/` → детали корректны

> **Примечание:** в текущей кодовой базе создание товара — `POST /api/v1/products/` и доступно поставщику (`get_current_active_supplier`); отдельного endpoint `/api/v1/admin/products/` нет. Если меняется RBAC — актуализировать сценарий.

### Сценарий 5: Поиск и фильтры

```
Главная → Поиск "телефон" → Фильтр по цене → Карточка товара
```

**Затрагиваемые модули:** `products`, `search`  
**Проверка:**
1. `GET /api/v1/products/?q=телефон` → результаты
2. Фильтр `?min_price=1000&max_price=50000` → отфильтровано
3. Переход на карточку → данные корректны

### Как проверять

| Слой | Как проверить |
|------|--------------|
| Backend | `make test-backend` или `curl` |
| Frontend | `make test-frontend` + ручной просмотр |
| E2E | `make test-e2e` или ручной проход |

> **Важно:** Не нужно проверять ВСЕ сценарии для каждой задачи.  
> Проверяй только те, где затронут твой модуль.  
> Для ручных проверок сбрасывай rate limiter (см. [Rule: Known Pitfalls](known-pitfalls.md)).

---
