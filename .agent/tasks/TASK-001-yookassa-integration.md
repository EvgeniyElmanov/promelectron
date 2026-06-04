# [P0] Интеграция ЮKassa — План реализации

> **Статус:** План составлен, готов к выполнению  
> **Агент:** backend-dev (основная роль), frontend-dev, e2e-tester  
> **Оценка:** 2 недели  
> **Зависимости:** BLK-006 (Alembic миграция) — нужно закрыть перед миграцией Payment

---

## Контекст

- Уже есть mock-оплата: `PaymentService.create_payment()` создаёт запись с `provider_payment_id="mock_..."`
- Есть endpoints: `POST /payments/{order_id}/`, `POST /payments/{payment_id}/confirm/`, `GET /payments/{payment_id}/`, `POST /payments/{payment_id}/cancel/`
- Mock-оплата работает через ручной `confirm_payment` endpoint (имитация callback)
- ЮKassa API: `https://api.yookassa.ru/v3`, Basic Auth (shopId + secretKey)
- Python SDK: `pip install yookassa`
- Тестовые данные: `shopId=54401`, `secretKey=test_Fh8hUAVVBGUGbjmlzba6TB0iyUbos_lueTHE-axOwM0`
- Тестовая карта: `5555555555554444`, срок `12/20`, CVV `000`

---

## Архитектура интеграции

```
Пользователь → Frontend → POST /payments/{order_id}/
                              │
                              ▼
                    ┌─────────────────┐
                    │ PaymentService  │
                    │ create_payment  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌─────────┐   ┌──────────┐   ┌──────────┐
        │  Order  │   │ YooKassa │   │ Payment  │
        │  (БД)   │   │   API    │   │  (БД)    │
        └─────────┘   └────┬─────┘   └──────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │ confirmation│
                    │    _url     │
                    └──────┬──────┘
                           │
              Пользователь ◄┘ (редирект)
                           │
                    ┌──────┴──────┐
                    │  ЮKassa UI   │
                    │  (оплата)    │
                    └──────┬──────┘
                           │
              Пользователь ► return_url
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
    POST /payments/yookassa/webhook/   (или polling fallback)
              │
              ▼
    ┌─────────────────┐
    │ Webhook Handler │ → обновляет Payment + Order статусы
    └─────────────────┘
```

---

## Phase 1: Инфраструктура (1 день)

### 1.1 Установка SDK
```bash
# backend/requirements.txt
yookassa>=3.0.0
```

### 1.2 Env vars + Settings
**`.env.example`:**
```bash
# --- YooKassa ---
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_RETURN_URL=http://localhost:5173/payment/success
YOOKASSA_TEST_MODE=true
```

**`backend/src/app/core/config.py`:**
- Добавить поля: `yookassa_shop_id`, `yookassa_secret_key`, `yookassa_return_url`, `yookassa_test_mode`

### 1.3 Alembic миграция
Добавить в модель `Payment`:
```python
# backend/src/app/models/payment.py
yookassa_payment_id = Column(String, nullable=True, index=True)
payment_method_type = Column(String, nullable=True)  # bank_card, sbp и т.д.
capture_status = Column(String, nullable=True)  # automatic / manual
metadata_json = Column(JSON, nullable=True)  # для metadata
```

> **⚠️ Блокер:** BLK-006 (malformed Alembic revision) нужно закрыть ДО этой миграции.

---

## Phase 2: Backend — YooKassaService (2-3 дня)

### 2.1 Создать `backend/src/app/services/yookassa_service.py`

```python
import uuid
from yookassa import Configuration, Payment as YooPayment

class YooKassaService:
    @staticmethod
    def _configure():
        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key
    
    @staticmethod
    def create_payment(amount: Decimal, description: str, order_id: int, return_url: str):
        """Создать платёж в ЮKassa."""
        YooKassaService._configure()
        
        idempotence_key = str(uuid.uuid4())
        
        payment = YooPayment.create({
            "amount": {
                "value": str(amount),
                "currency": "RUB"
            },
            "capture": True,  # автоматическое списание
            "confirmation": {
                "type": "redirect",
                "return_url": return_url
            },
            "description": description,
            "metadata": {
                "order_id": str(order_id)
            }
        }, idempotence_key)
        
        return payment  # YooPayment object
    
    @staticmethod
    def get_payment(payment_id: str):
        """Получить статус платежа из ЮKassa."""
        YooKassaService._configure()
        return YooPayment.find_one(payment_id)
```

### 2.2 Обновить `PaymentService.create_payment()`

```python
async def create_payment(order_id: int, user_id: int, db: AsyncSession) -> Payment:
    # ... существующая проверка заказа ...
    
    # Создаём платёж в ЮKassa
    yookassa_payment = YooKassaService.create_payment(
        amount=order.total_price,
        description=f"Заказ №{order.id}",
        order_id=order.id,
        return_url=f"{settings.frontend_url}/payment/success"
    )
    
    payment = Payment(
        order_id=order.id,
        amount=order.total_price,
        status="pending",
        provider_payment_id=yookassa_payment.id,  # реальный ID ЮKassa
        yookassa_payment_id=yookassa_payment.id,
        payment_method_type=yookassa_payment.payment_method.type if yookassa_payment.payment_method else None,
        capture_status="automatic" if yookassa_payment.capture else "manual",
        metadata_json={"confirmation_url": yookassa_payment.confirmation.confirmation_url}
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    
    return payment
```

### 2.3 Обновить `payments.py` API

```python
@router.post("/{order_id}/", response_model=PaymentCreateResponse)
async def create_payment(...):
    payment = await PaymentService.create_payment(...)
    confirmation_url = payment.metadata_json.get("confirmation_url") if payment.metadata_json else None
    return PaymentCreateResponse(
        payment_id=payment.id,
        status=payment.status,
        confirmation_url=confirmation_url,  # реальный URL ЮKassa
        amount=payment.amount,
    )
```

**Schema `PaymentCreateResponse`:**
```python
class PaymentCreateResponse(BaseModel):
    payment_id: int
    status: str
    confirmation_url: Optional[str] = None  # URL для редиректа
    amount: Decimal
```

### 2.4 Webhook endpoint `POST /payments/yookassa/webhook/`

```python
@router.post("/yookassa/webhook/")
async def yookassa_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Входящее уведомление от ЮKassa."""
    body = await request.body()
    payload = await request.json()
    
    # TODO: Проверка подписи (см. Phase 2.5)
    
    event = payload.get("event")
    payment_obj = payload.get("object", {})
    yookassa_id = payment_obj.get("id")
    metadata = payment_obj.get("metadata", {})
    order_id = int(metadata.get("order_id", 0))
    
    if event == "payment.succeeded":
        await PaymentService.confirm_payment_by_provider(
            provider_payment_id=yookassa_id,
            db=db
        )
    elif event == "payment.canceled":
        await PaymentService.cancel_payment_by_provider(
            provider_payment_id=yookassa_id,
            db=db
        )
    
    return {"status": "ok"}
```

### 2.5 Проверка подписи webhook

```python
import hmac
import hashlib

def verify_webhook_signature(body: bytes, signature: str, secret_key: str) -> bool:
    """Проверить подпись уведомления ЮKassa."""
    expected = hmac.new(
        secret_key.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

> **Примечание:** ЮKassa отправляет подпись в заголовке `Authorization` или как часть IPN. Нужно уточнить точный формат из документации. Возможно, используется `SHA-256` HMAC.

### 2.6 Новые методы PaymentService

```python
@staticmethod
async def confirm_payment_by_provider(provider_payment_id: str, db: AsyncSession) -> Payment:
    """Подтвердить платёж по ID провайдера (из webhook)."""
    result = await db.execute(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        .options(selectinload(Payment.order).selectinload(Order.items))
    )
    payment = result.scalars().first()
    
    if not payment or payment.status == "paid":
        return payment
    
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    payment.order.status = "paid"
    await db.commit()
    
    # Email + notification (существующий код)
    ...
    
    return payment

@staticmethod
async def cancel_payment_by_provider(provider_payment_id: str, db: AsyncSession) -> Payment:
    """Отменить платёж по ID провайдера (из webhook)."""
    result = await db.execute(
        select(Payment).where(Payment.provider_payment_id == provider_payment_id)
    )
    payment = result.scalars().first()
    
    if not payment or payment.status == "paid":
        return payment
    
    payment.status = "cancelled"
    payment.order.status = "cancelled"
    await db.commit()
    return payment
```

---

## Phase 3: Frontend (2 дня)

### 3.1 Обновить `useCart` / Checkout flow

```javascript
// После создания заказа
const createPayment = async (orderId) => {
  const { data } = await api.post(`/payments/${orderId}/`);
  if (data.confirmation_url) {
    window.location.href = data.confirmation_url; // Редирект на ЮKassa
  }
};
```

### 3.2 Страница возврата `/payment/success`

```vue
<!-- PaymentSuccessView.vue -->
<template>
  <div>
    <h1 v-if="loading">Проверяем оплату...</h1>
    <h1 v-else-if="paid">✅ Заказ оплачен!</h1>
    <h1 v-else>❌ Оплата не завершена</h1>
  </div>
</template>

<script setup>
// После return_url от ЮKassa — запрашиваем статус платежа
// Или просто показываем "Проверяем..." и ждём webhook
</script>
```

### 3.3 Обновить `CheckoutButton`

- Убрать mock-логику
- Добавить редирект на `confirmation_url`
- Добавить обработку ошибок

---

## Phase 4: Тестирование (2 дня)

### 4.1 Backend тесты
- `test_yookassa_service.py` — мокаем YooPayment.create/find_one
- `test_payments_webhook.py` — тест webhook endpoint
  - payment.succeeded → статус paid
  - payment.canceled → статус cancelled
  - Невалидная подпись → 400

### 4.2 E2E тесты
- Сценарий: Гость → добавляет в корзину → checkout → оплата тестовой картой → success
- Использовать тестовую карту `5555555555554444`

### 4.3 Ручное тестирование
```bash
# 1. Создать заказ
# 2. Создать платёж → получить confirmation_url
# 3. Открыть URL → оплатить тестовой картой
# 4. Проверить webhook / статус заказа
```

---

## API Changes

### Новые / изменённые endpoints

| Метод | Путь | Изменение |
|-------|------|-----------|
| POST | `/api/v1/payments/{order_id}/` | Теперь возвращает реальный `confirmation_url` от ЮKassa |
| POST | `/api/v1/payments/yookassa/webhook/` | **Новый** — входящие уведомления от ЮKassa |
| POST | `/api/v1/payments/{payment_id}/confirm/` | **Удалить** — больше не нужен (mock) |

### Schema changes

```python
# PaymentOut — добавить
yookassa_payment_id: Optional[str] = None
payment_method_type: Optional[str] = None
confirmation_url: Optional[str] = None  # из metadata_json

# PaymentCreateResponse — уже есть confirmation_url
```

---

## Env vars (добавить)

```bash
YOOKASSA_SHOP_ID=54401
YOOKASSA_SECRET_KEY=test_Fh8hUAVVBGUGbjmlzba6TB0iyUbos_lueTHE-axOwM0
YOOKASSA_RETURN_URL=http://localhost:5173/payment/success
YOOKASSA_TEST_MODE=true
```

---

## Риски

| Риск | Вероятность | Митигация |
|------|------------|-----------|
| SDK `yookassa` синхронный | Высокая | Запускать в `asyncio.to_thread()` или использовать httpx напрямую |
| Webhook не доставляется | Средняя | Реализовать polling fallback (cron/check_pending_payments) |
| Подпись webhook сложная | Средняя | Начать без проверки подписи (тест), добавить позже |
| Idempotency key | Средняя | Генерировать UUID4, сохранять в metadata_json |

---

## Definition of Done

- [ ] `POST /payments/{order_id}/` создаёт реальный платёж в ЮKassa
- [ ] В ответе приходит `confirmation_url` для редиректа
- [ ] Webhook `POST /payments/yookassa/webhook/` обрабатывает `payment.succeeded` и `payment.canceled`
- [ ] После оплаты статус заказа меняется на "paid"
- [ ] Email + notification отправляются (существующий код работает)
- [ ] Backend тесты проходят (pytest)
- [ ] E2E тест проходит с тестовой картой
- [ ] `.env.example` обновлён
- [ ] `PROJECT_CONTEXT.md` обновлён (API Inventory)
