# План интеграции ЮKassa — Promelectron

> **Дата:** 2026-06-02
> **Статус:** Планирование завершено, готов к реализации
> **Роль:** project-manager → backend-dev / frontend-dev / e2e-tester
> **Спринт:** Sprint 1 (2026-06-01 — 2026-06-14)

---

## 1. Резюме

Заменить mock-оплату на реальную интеграцию с **ЮKassa API v3** через официальный Python SDK (`yookassa`).

**Текущее состояние:**
- Создание платежа → генерация `mock_<order_id>_<timestamp>`
- Подтверждение → ручной `POST /payments/{id}/confirm` (mock endpoint)
- Frontend → ввод фейковых данных карты, имитация задержки

**Целевое состояние:**
- Создание платежа → реальный запрос в ЮKassa API → получение `confirmation_url`
- Пользователь редиректится на страницу оплаты ЮKassa
- После оплаты ЮKassa шлёт webhook `payment.succeeded` → обновление статуса
- Отмена/возврат через API ЮKassa

---

## 2. Архитектура интеграции

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│  ЮKassa API │
│  Checkout   │     │   Backend   │     │   (yookassa)│
└─────────────┘     └──────┬──────┘     └─────────────┘
       ▲                   │
       │                   │ webhook
       │                   ▼
       │            ┌─────────────┐
       └────────────│  Webhook    │
                    │  Handler    │
                    └─────────────┘
```

**Поток данных:**
1. Пользователь нажимает «Оплатить» → frontend вызывает `POST /payments/{order_id}/`
2. Backend создаёт платёж в ЮKassa через SDK (`Payment.create`)
3. Backend возвращает `confirmation_url` (URL ЮKassa)
4. Frontend редиректит пользователя на `confirmation_url`
5. Пользователь оплачивает на странице ЮKassa
6. ЮKassa отправляет webhook `payment.succeeded` на `POST /payments/yookassa/webhook/`
7. Backend валидирует подпись webhook → обновляет заказ → отправляет email/уведомление

---

## 3. Изменения в модели данных

### 3.1 Таблица `payments` (Alembic миграция)

```sql
ALTER TABLE payments
  ADD COLUMN yookassa_payment_id VARCHAR(64) UNIQUE,  -- ID платежа в ЮKassa (was provider_payment_id)
  ADD COLUMN yookassa_status VARCHAR(32),              -- pending / waiting_for_capture / succeeded / canceled
  ADD COLUMN confirmation_url TEXT,                    -- URL для редиректа пользователя
  ADD COLUMN payment_method_type VARCHAR(32),          -- bank_card / sbp / sberpay и т.д.
  ADD COLUMN captured_amount NUMERIC(10,2),            -- сумма списания (для двухстадийных)
  ADD COLUMN refunded_amount NUMERIC(10,2) DEFAULT 0,  -- сумма возвратов
  ADD COLUMN metadata JSONB,                           -- metadata для ЮKassa
  ADD COLUMN yookassa_created_at TIMESTAMP,            -- время создания в ЮKassa
  ADD COLUMN updated_at TIMESTAMP;                     -- время последнего обновления

-- Переименование старого поля (опционально, для совместимости)
-- provider_payment_id → yookassa_payment_id
```

### 3.2 Перечисление статусов

| Наш статус | ЮKassa статус | Описание |
|-----------|---------------|----------|
| `pending` | `pending` | Создан, ждёт действия пользователя |
| `waiting_for_capture` | `waiting_for_capture` | Требуется подтверждение (двухстадийный) |
| `paid` | `succeeded` | Успешно оплачен |
| `cancelled` | `canceled` | Отменён |
| `refunded` | — | Возврат выполнен (частично или полностью) |

---

## 4. Задачи по реализации

### Этап 1: Инфраструктура и конфигурация (backend-dev, 1 день)

**Задача: YK-001**

- [ ] Добавить `yookassa` в `backend/requirements.txt`
- [ ] Добавить env vars:
  ```
  YOOKASSA_SHOP_ID=
  YOOKASSA_SECRET_KEY=
  YOOKASSA_WEBHOOK_SECRET=          # для проверки подписи webhook (опционально)
  YOOKASSA_RETURN_URL_BASE=         # базовый URL для return_url (FRONTEND_URL)
  YOOKASSA_TEST_MODE=true           # true для тестовой среды
  ```
- [ ] Обновить `backend/src/app/core/config.py` → `Settings`
- [ ] Обновить `.env.example`
- [ ] Настроить SOPS / k8s secrets для production

**Критерии приёмки:**
- `pip install -r requirements.txt` успешно
- `Settings` читает YOOKASSA_* без ошибок
- Тестовые креды из архива работают в dev-режиме

---

### Этап 2: Alembic миграция (backend-dev, 1 день)

**Задача: YK-002** (зависит от YK-001, BLK-006)

- [ ] Создать миграцию `alembic revision -m "yookassa payment fields"`
- [ ] Добавить поля из раздела 3.1
- [ ] Мигрировать существующие `provider_payment_id` → `yookassa_payment_id`
- [ ] `alembic upgrade head` проходит успешно

**Критерии приёмки:**
- Миграция применяется без ошибок
- Старые данные сохранены
- Тестовая БД проходит `alembic upgrade head`

---

### Этап 3: YooKassaService (backend-dev, 2 дня)

**Задача: YK-003** (зависит от YK-001, YK-002)

Создать `backend/src/app/services/yookassa_service.py`:

```python
class YooKassaService:
    @staticmethod
    async def create_payment(
        order: Order,
        idempotence_key: str,
    ) -> dict:
        """
        Создаёт платёж в ЮKassa.
        Возвращает dict с yookassa_payment_id, confirmation_url, status.
        """
        # Используем yookassa SDK
        # amount, currency=RUB, capture=true, confirmation.type=redirect
        # return_url = f"{FRONTEND_URL}/payment/success?order_id={order.id}"
        # metadata = {"order_id": str(order.id), "user_id": str(order.user_id)}
        # description = f"Заказ №{order.id}"

    @staticmethod
    async def get_payment(yookassa_payment_id: str) -> dict:
        """Получить статус платежа из ЮKassa."""

    @staticmethod
    async def cancel_payment(yookassa_payment_id: str, idempotence_key: str) -> dict:
        """Отменить платёж в ЮKassa (только waiting_for_capture)."""

    @staticmethod
    async def create_refund(
        yookassa_payment_id: str,
        amount: Decimal,
        idempotence_key: str,
    ) -> dict:
        """Создать возврат."""
```

**Ключевые моменты:**
- Использовать `capture: true` (одностадийный платёж) — проще, деньги сразу списываются
- `idempotence_key` — UUID4, одинаковый при повторных попытках
- `metadata` — обязательно передавать `order_id` для связи при webhook
- Обработка ошибок ЮKassa: `BadRequestError`, `ForbiddenError`, `NotFoundError`, `TooManyRequestsError`, `UnauthorizedError`
- Логирование всех запросов/ответов (без secret key)

**Критерии приёмки:**
- Unit-тесты с моками SDK (pytest + unittest.mock)
- Обработка всех HTTP-кодов (200, 400, 401, 403, 404, 429, 500)
- Idempotence key корректно генерируется и переиспользуется

---

### Этап 4: Обновление PaymentService (backend-dev, 1 день)

**Задача: YK-004** (зависит от YK-003)

Обновить `backend/src/app/services/payment_service.py`:

- [ ] `create_payment()` → вызывает `YooKassaService.create_payment()`
  - Сохраняет `yookassa_payment_id`, `confirmation_url`, `yookassa_status`
  - Не создаёт дубли (проверка на существующий платёж для order)
- [ ] Удалить `confirm_payment()` — заменяется webhook
- [ ] `cancel_payment()` → вызывает `YooKassaService.cancel_payment()` (если `waiting_for_capture`)
- [ ] Добавить `handle_webhook(payload: dict, signature: str)` → валидация + обновление статуса
- [ ] Добавить `process_successful_payment(payment: Payment)` → очистка корзины, email, уведомление

**Критерии приёмки:**
- `create_payment` создаёт реальный платёж в тестовой среде ЮKassa
- `handle_webhook` корректно обновляет статус заказа
- Повторный webhook `payment.succeeded` — идемпотентно (не дублирует email/уведомление)

---

### Этап 5: API Endpoints (backend-dev, 1 день)

**Задача: YK-005** (зависит от YK-004)

Обновить `backend/src/app/api/payments.py`:

| Метод | Путь | Изменение |
|-------|------|-----------|
| `POST` | `/payments/{order_id}/` | Создаёт платёж в ЮKassa, возвращает `confirmation_url` |
| `GET` | `/payments/{payment_id}/` | Информация о платеже (из БД) |
| `POST` | `/payments/{payment_id}/cancel/` | Отмена (через ЮKassa API, если возможно) |
| `POST` | `/payments/yookassa/webhook/` | **Новый** — входящий webhook от ЮKassa |
| ~~`POST`~~ | ~~`/payments/{payment_id}/confirm/`~~ | **Удалить** — mock endpoint |

**Webhook endpoint:**
- Без auth (ЮKassa не использует JWT)
- Проверка подписи `SHA-256 HMAC` (если настроен webhook secret) или IP whitelist
- Идемпотентность: проверка `object.status` + текущий статус в БД
- Ответ `200 OK` в любом случае (чтобы ЮKassa не ретраила)
- Логирование raw payload

**Критерии приёмки:**
- `POST /payments/{order_id}/` возвращает `confirmation_url`
- Webhook endpoint отвечает 200
- Подпись webhook валидируется (если secret задан)

---

### Этап 6: Frontend — редирект на ЮKassa (frontend-dev, 2 дня)

**Задача: YK-006** (зависит от YK-005)

Обновить `frontend/src/views/Checkout.vue`:

```javascript
// processPayment — новая логика
const processPayment = async () => {
  processing.value = true;
  try {
    const { data } = await api.post(`/payments/${orderId.value}/`);
    // Редирект на страницу оплаты ЮKassa
    window.location.href = data.confirmation_url;
  } catch (err) {
    toast(err.response?.data?.detail || 'Ошибка при создании платежа', 'error');
  } finally {
    processing.value = false;
  }
};
```

Убрать:
- Поля ввода карты (`cardNumber`, `cardExpiry`, `cardCvv`, `cardHolder`)
- Валидацию карты
- `confirm_payment` вызов
- Имитацию задержки

Добавить:
- Страница `PaymentSuccess.vue` — `/payment/success?order_id={id}`
  - Показывает статус заказа
  - Опционально: polling `GET /orders/{id}/` до статуса `paid`
- Страница `PaymentFailed.vue` — `/payment/failed?order_id={id}`
  - Предлагает повторить оплату

**Критерии приёмки:**
- Нажатие «Оплатить» → редирект на yoomoney.ru
- После оплаты → возврат на `/payment/success`
- Статус заказа обновляется (polling или websocket)

---

### Этап 7: Backend тесты (backend-dev, 2 дня)

**Задача: YK-007** (зависит от YK-005)

- [ ] Тесты `YooKassaService` — моки SDK
  - `create_payment` — успех, ошибка 400, ошибка 401
  - `cancel_payment` — успех, ошибка "нельзя отменить succeeded"
  - `create_refund` — успех
- [ ] Тесты webhook handler
  - `payment.succeeded` — обновление статуса
  - `payment.canceled` — обновление статуса
  - Повторный webhook — idempotence
  - Невалидная подпись — 200 (чтобы не ретраил), но без обработки
- [ ] Тесты API endpoints
  - `POST /payments/{order_id}/` — 201, 404 (order not found), 400 (already exists)
  - `POST /payments/{payment_id}/cancel/` — 200, 400 (paid)
- [ ] Интеграционный тест с тестовой картой `5555555555554444`

**Критерии приёмки:**
- `pytest -x` — 100% зелёные
- Покрытие нового кода ≥ 90%

---

### Этап 8: E2E тест с тестовой картой (e2e-tester, 2 дня)

**Задача: YK-008** (зависит от YK-006, YK-007)

Playwright сценарий:

```javascript
test('Оплата тестовой картой ЮKassa', async ({ page }) => {
  // 1. Авторизоваться
  // 2. Добавить товар в корзину
  // 3. Оформить заказ
  // 4. Нажать «Оплатить»
  // 5. Дождаться редиректа на yoomoney.ru (или demo)
  // 6. Ввести тестовую карту 5555555555554444, 12/20, 000
  // 7. Подтвердить оплату
  // 8. Дождаться редиректа обратно на /payment/success
  // 9. Проверить статус заказа = paid
});
```

**Тестовые данные:**
- Карта: `5555555555554444`
- Срок: `12/20`
- CVV: `000`
- Shop ID: `54401`
- Secret Key: `test_Fh8hUAVVBGUGbjmlzba6TB0iyUbos_lueTHE-axOwM0`

**Критерии приёмки:**
- E2E тест проходит в CI
- Скриншоты success/fail страниц

---

## 5. Безопасность

| Угроза | Митигация |
|--------|-----------|
| Подделка webhook | Проверка подписи `SHA-256 HMAC` + IP whitelist (опционально) |
| Повторный webhook | Идемпотентность: проверка `yookassa_status` + `paid_at` |
| Утечка secret key | Только в env, никогда в логах/ответах |
| Man-in-the-middle | HTTPS только (production) |
| Race condition на stock | `SELECT FOR UPDATE` при создании заказа (уже реализовано) |
| Переплата | Сверка `amount.value` из webhook с `order.total_price` |
| Подмена order_id | `metadata.order_id` из webhook + проверка в БД |

---

## 6. Зависимости и риски

### Блокеры

| ID | Влияние | Решение |
|----|---------|---------|
| BLK-006 (Alembic malformed) | YK-002 блокирован | Исправить revision ID перед миграцией |

### Риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| ЮKassa SDK синхронный | Средняя | Среднее | Использовать `asyncio.to_thread` для вызовов SDK |
| Webhook доставка | Низкая | Высокое | Polling fallback (`GET /payments/{id}/`) на success-странице |
| Тестовая среда недоступна | Низкая | Среднее | Моки SDK для unit-тестов |
| Двухстадийные платежи не нужны сейчас | — | — | Использовать `capture: true` |

---

## 7. Оценка времени

| Этап | Задача | Длительность | Исполнитель |
|------|--------|--------------|-------------|
| 1 | YK-001: Конфиг + SDK | 1 день | backend-dev |
| 2 | YK-002: Миграция | 1 день | backend-dev |
| 3 | YK-003: YooKassaService | 2 дня | backend-dev |
| 4 | YK-004: PaymentService | 1 день | backend-dev |
| 5 | YK-005: API endpoints | 1 день | backend-dev |
| 6 | YK-006: Frontend | 2 дня | frontend-dev |
| 7 | YK-007: Backend тесты | 2 дня | backend-dev |
| 8 | YK-008: E2E тест | 2 дня | e2e-tester |
| **Итого** | | **12 дней** | |
| **Параллельно** | | **~8 дней** | frontend и backend параллельно после YK-005 |

---

## 8. Acceptance Criteria (Общие)

- [ ] Пользователь может оплатить заказ реальной картой через ЮKassa
- [ ] После оплаты статус заказа меняется на `paid`
- [ ] Email и push-уведомление отправляются при успешной оплате
- [ ] Webhook корректно обрабатывается с проверкой подписи
- [ ] Отмена неоплаченного платежа работает
- [ ] Возврат (refund) доступен из админки
- [ ] Тесты: backend 123+/123+, E2E зелёные
- [ ] Тестовая карта `5555555555554444` проходит в E2E

---

## 9. Порядок выполнения

```
YK-001 ──▶ YK-002 ──▶ YK-003 ──▶ YK-004 ──▶ YK-005 ──┬──▶ YK-007
                                                        │
                                              (параллельно)
                                                        │
                                              YK-006 ───┴──▶ YK-008
```

**Рекомендуемый старт:**
1. backend-dev: YK-001 + YK-002 (2 дня)
2. backend-dev: YK-003 + YK-004 + YK-005 (4 дня)
3. frontend-dev: YK-006 (2 дня, параллельно с YK-005)
4. backend-dev: YK-007 (2 дня)
5. e2e-tester: YK-008 (2 дня)

---

*План подготовлен project-manager на основе анализа архива документации ЮKassa и текущего состояния кодовой базы Promelectron.*
