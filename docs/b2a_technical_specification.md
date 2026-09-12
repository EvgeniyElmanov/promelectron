# Техническое задание: Адаптация системы под B2A (Business-to-Agent)

**Цель:** Сделать каталог, коммерческие условия и процесс оформления заказов доступными для взаимодействия и совершения сделок автономными ИИ-агентами без прямого участия человека через UI.

---

## 1. Data Layer: Микроразметка и системные файлы

### 1.1. Внедрение JSON-LD (Schema.org)
На все страницы карточек товаров/услуг необходимо добавить структурированные данные `Product` и `Offer`. Это позволит ИИ-агентам извлекать точную цену, валюту, статус наличия и ключевые параметры без парсинга HTML DOM.

**Пример внедрения в `<head>`:**

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org/",
  "@type": "Product",
  "name": "Интерактивный курс по аналитике данных",
  "image": [
    "https://example.com/photos/1x1/photo.jpg"
  ],
  "description": "Профессиональный курс обучения аналитике данных, длительность 6 месяцев, с практикой.",
  "sku": "COURSE-ANALYTICS-01",
  "offers": {
    "@type": "Offer",
    "url": "https://example.com/courses/analytics",
    "priceCurrency": "RUB",
    "price": "49000.00",
    "priceValidUntil": "2026-12-31",
    "itemCondition": "https://schema.org/NewCondition",
    "availability": "https://schema.org/InStock",
    "seller": {
      "@type": "Organization",
      "name": "Example Academy"
    }
  }
}
</script>
```

### 1.2. Создание файла `llms.txt`
Разместить файл `llms.txt` в корневом каталоге сайта (`/llms.txt`). Он служит сводной инструкцией для языковых моделей и парсеров ИИ-агентов, описывая сущности и точки входа.

**Пример `/llms.txt`:**

```txt
# Example Company

> Компания предоставляет образовательные программы и курсы по IT и аналитике.

## Core Products
- [Аналитика данных](https://example.com/courses/analytics): Полный курс с нуля.
- [Python-разработка](https://example.com/courses/python): Базовый и продвинутый уровни.

## API & Agent Access
- OpenAPI Spec: https://api.example.com/v1/openapi.json
- MCP Endpoint: https://api.example.com/mcp
- Machine Checkout Docs: https://docs.example.com/b2a/checkout
```

---

## 2. API-First & Machine-Readable Responses

### 2.1. Спецификация OpenAPI 3.0 (Swagger)
Все публичные и сервисные эндпоинты, доступные для агентов, должны документироваться и валидироваться по актуальной схеме `OpenAPI 3.0`.

**Пример спецификации `openapi.json` (фрагмент):**

```json
{
  "openapi": "3.0.1",
  "info": {
    "title": "B2A Commerce API",
    "version": "1.0.0"
  },
  "paths": {
    "/api/v1/products/{id}": {
      "get": {
        "summary": "Получить данные о товаре и остатках",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Успешный ответ",
            "content": {
              "application/json": {
                "schema": {
                  "$ref": "#/components/schemas/Product"
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 2.2. Стандартизация ошибок (RFC 7807 Problem Details)
ИИ-агент должен получать машиночитаемые ответы об ошибках с подробной структурой, чтобы автоматически приниматься за обработку исключений (например, обновить токен или изменить параметры запроса).

**Пример ответа сервера при ошибке `400 Bad Request`:**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/problem+json

{
  "type": "https://example.com/probs/out-of-stock",
  "title": "Товара нет в наличии",
  "status": 400,
  "detail": "Запрошенное количество (5) превышает доступный остаток (2).",
  "instance": "/api/v1/orders/check",
  "available_stock": 2
}
```

### 2.3. Поддержка Model Context Protocol (MCP)
Реализовать поддержку протокола **MCP** (Model Context Protocol) для интеграции поиска и формирования заказов непосредственно в диалоговый контекст ИИ-моделей.

**Пример MCP Tool Definition (JSON-RPC) для ИИ-агента:**

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "result": {
    "tools": [
      {
        "name": "search_products",
        "description": "Поиск товаров по ключевым словам и максимальной цене",
        "inputSchema": {
          "type": "object",
          "properties": {
            "query": { "type": "string" },
            "max_price": { "type": "number" }
          },
          "required": ["query"]
        }
      }
    ]
  }
}
```

---

## 3. Авторизация и транзакции (Machine Auth)

Веб-формы, CAPTCHA и 2FA через SMS делают прямое оформление покупки ИИ-агентом невозможным. Необходим шлюз **Machine-to-Machine (M2M)**.

### 3.1. OAuth 2.0 Client Credentials Flow
Пользователь выпускает клиентские ключи (`client_id`, `client_secret`) в личном кабинете и передает их своему ИИ-агенту с ограниченными правами (например, `read:catalog`, `write:orders`).

**Пример запроса на получение токена:**

```bash
POST /oauth/token HTTP/1.1
Host: auth.example.com
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id=agent_client_abc123
&client_secret=secret_xyz789
&scope=write:orders
```

**Ответ сервера:**

```json
{
  "access_token": "eyJhbGciOiJKV1QiLC...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "write:orders"
}
```

### 3.2. Автоматическое создание заказа (Checkout Endpoint)

Эндпоинт принимает прямые параметры заказа и возвращает результат подтвержденного списания или создания транзакции.

**Запрос от агента (`POST /api/v1/orders`):**

```json
{
  "item_id": "COURSE-ANALYTICS-01",
  "quantity": 1,
  "currency": "RUB",
  "agreed_price": 49000.00,
  "customer_metadata": {
    "agent_id": "claude-3-5-sonnet-user-881",
    "delivery_email": "client@example.com"
  }
}
```

**Успешный ответ сервера (`201 Created`):**

```json
{
  "order_id": "ORD-2026-99412",
  "status": "confirmed",
  "total_amount": 49000.00,
  "payment_status": "settled",
  "receipt_url": "https://example.com/receipts/ORD-2026-99412.pdf"
}
```

---

## 4. Чек-лист готовности для приемки

1. [ ] Вся номенклатура и прайсы покрыты корректной микроразметкой `Schema.org` (JSON-LD).
2. [ ] В корневом каталоге сайта отдается валидный файл `/llms.txt`.
3. [ ] Подготовлена спецификация `OpenAPI 3.0` для B2A-эндпоинтов.
4. [ ] Настроена выдача ошибок в формате `RFC 7807 (Problem Details)`.
5. [ ] Внедрен метод M2M-авторизации (OAuth2) и эндпоинты оформления заказов без CAPTCHA и 2FA.
