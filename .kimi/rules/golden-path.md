# Golden Path — критичные сценарии, которые нельзя ломать

> **Правило:** Если твои изменения затрагивают модуль из списка ниже — перед финишем проверь сценарий.  
> Не обязательно писать тест, достаточно ручной проверки (curl / UI / Playwright).

---

## Сценарий 1: Полный путь покупки (авторизованный)

```
Регистрация → Логин → Каталог → Карточка товара → Корзина → Checkout → Оплата → Успех
```

**Затрагиваемые модули:** `auth`, `products`, `cart`, `orders`, `payments`, `notifications`  
**Проверка:**
1. `POST /auth/register/` → 201
2. `POST /auth/login/` → JWT токен
3. `GET /products/` → список товаров
4. `POST /cart/` → добавить в корзину
5. `POST /orders/` → создать заказ
6. `POST /payments/{order_id}/` → создать платёж (confirmation_url)
7. `GET /orders/{id}/` → статус "paid" после webhook
8. WebSocket уведомление пришло

---

## Сценарий 2: Полный путь покупки (гость)

```
Каталог (гость) → Корзина (localStorage) → Checkout → Login → Merge корзины → Оплата
```

**Затрагиваемые модули:** `products`, `guest-cart`, `cart`, `auth`, `orders`, `payments`  
**Проверка:**
1. Гость добавляет товар (localStorage)
2. Гость идёт в checkout → redirect на `/login`
3. После login `POST /cart/merge/` → корзина объединена
4. `POST /orders/` → заказ создан
5. `POST /payments/{order_id}/` → платёж создан

---

## Сценарий 3: OAuth вход

```
Yandex/Google OAuth → Callback → Авторизация → Профиль
```

**Затрагиваемые модули:** `auth/yandex`, `auth/google`, `users`  
**Проверка:**
1. `GET /auth/yandex/` или `/auth/google/` → redirect
2. Callback → `POST /auth/yandex/` или `/auth/google/` → JWT + user
3. `GET /users/me/` → профиль загружен

---

## Сценарий 4: Админ-панель

```
Админ логин → CRUD товара → Товар виден в каталоге
```

**Затрагиваемые модули:** `auth`, `admin/products`, `products`  
**Проверка:**
1. Admin login → `POST /auth/login/` (role=admin)
2. `POST /admin/products/` → товар создан
3. `GET /products/` → новый товар в списке
4. `GET /products/{id}/` → детали корректны

---

## Сценарий 5: Поиск и фильтры

```
Главная → Поиск "телефон" → Фильтр по цене → Карточка товара
```

**Затрагиваемые модули:** `products`, `search`  
**Проверка:**
1. `GET /products/search/?q=телефон` → результаты
2. Фильтр `?min_price=1000&max_price=50000` → отфильтровано
3. Переход на карточку → данные корректны

---

## Как проверять

| Слой | Как проверить |
|------|--------------|
| Backend | `curl` или `pytest` |
| Frontend | `npm test -- --run` + ручной просмотр |
| E2E | `npx playwright test` или ручной проход |

> **Важно:** Не нужно проверять ВСЕ сценарии для каждой задачи.  
> Проверяй только те, где затронут твой модуль.
