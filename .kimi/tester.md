# 🤖 Autonomous Tester Agent

## Что умеет

Агент выполняет E2E тестирование сайта **автономно** — от лица пользователя, админа или поставщика:
- Сам регистрируется со случайными данными
- Добавляет/редактирует товары
- Проходит весь флоу: каталог → карточка → корзина → заказ → оплата
- Проверяет UI на баги (перекрытия, ошибки консоли, layout shift)
- Проверяет API на 500/404/401
- Сохраняет отчёт с скриншотами

## Архитектура

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Persona    │────▶│  Scenario    │────▶│  Playwright  │
│  (роль +     │     │  (что делать)│     │  MCP (браузер)│
│  тест-данные)│     │              │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
        │                                          │
        └──────────────────────────────────────────┘
                           │
                    ┌──────────────┐
                    │  Bug Report  │
                    │  (скриншот + │
                    │   шаги + API)│
                    └──────────────┘
```

## 3 слоя автоматизации

### 1. Persona System — роли

Каждая роль = объект с:
- `email` / `password` — креды (генерируются на лету)
- `role` — `user` | `admin` | `supplier`
- `actions` — что может делать
- `assertions` — что должно видеть

```js
// tests/agent/personas.js
export const personas = {
  user: {
    name: 'Обычный покупатель',
    can: ['register', 'browse', 'add_to_cart', 'checkout', 'view_orders', 'add_review', 'add_favorite'],
    shouldSee: ['search-bar', 'product-card', 'cart-link', 'category-chips'],
    shouldNotSee: ['admin-panel', 'supplier-dashboard'],
  },
  admin: {
    name: 'Администратор',
    can: ['login', 'view_admin', 'manage_categories', 'manage_users', 'view_orders', 'block_user'],
    shouldSee: ['admin-dashboard', 'users-table', 'categories-table', 'orders-table'],
    shouldNotSee: ['supplier-products'],
  },
  supplier: {
    name: 'Поставщик',
    can: ['register_as_supplier', 'add_product', 'edit_product', 'delete_product', 'view_my_products'],
    shouldSee: ['supplier-dashboard', 'my-products-list', 'product-form'],
    shouldNotSee: ['admin-panel'],
  },
};
```

### 2. Scenario Library — сценарии

Каждый сценарий = шаги с `action` + `assertion`:

```js
// tests/agent/scenarios.js
export const scenarios = {
  fullPurchaseFlow: [
    { action: 'goto', target: '/' },
    { action: 'assert', selector: '[data-testid="product-card"]', expect: 'visible' },
    { action: 'click', selector: '[data-testid="product-card"]:first-child' },
    { action: 'assert', url: '/product/*' },
    { action: 'click', selector: '[data-testid="add-to-cart-button"]' },
    { action: 'assert', toast: 'Добавлено в корзину' },
    { action: 'click', selector: '[data-testid="cart-link"]' },
    { action: 'assert', url: '/cart' },
    { action: 'click', selector: '[data-testid="checkout-button"]' },
    // ...
  ],
  
  adminCategoryManagement: [
    { action: 'login', persona: 'admin' },
    { action: 'goto', target: '/admin' },
    { action: 'assert', selector: '[data-testid="admin-dashboard"]', expect: 'visible' },
    { action: 'click', selector: '[data-testid="categories-tab"]' },
    { action: 'click', selector: '[data-testid="add-category-btn"]' },
    { action: 'fill', selector: '[data-testid="category-name-input"]', value: 'Test Category {{random}}' },
    { action: 'click', selector: '[data-testid="save-category-btn"]' },
    { action: 'assert', selector: 'text=Test Category', expect: 'visible' },
  ],
  
  supplierAddProduct: [
    { action: 'register', persona: 'supplier' },
    { action: 'goto', target: '/my-products' },
    { action: 'click', selector: '[data-testid="add-product-btn"]' },
    { action: 'fill', selector: '[data-testid="product-name"]', value: 'Test Product {{random}}' },
    { action: 'fill', selector: '[data-testid="product-price"]', value: '9999' },
    { action: 'fill', selector: '[data-testid="product-stock"]', value: '10' },
    { action: 'click', selector: '[data-testid="save-product-btn"]' },
    { action: 'assert', selector: 'text=Test Product', expect: 'visible' },
  ],
};
```

### 3. Playwright MCP — движок

Используем уже настроенный MCP сервер `@playwright/mcp` из `.mcp.json`.

Ключевые команды MCP:
```
playwright_navigate(url)           — открыть страницу
playwright_click(selector)          — клик
playwright_fill(selector, value)    — заполнить поле
playwright_select_option(selector, value) — выбрать из селекта
playwright_screenshot()             — скриншот
playwright_evaluate(expression)     — выполнить JS в браузере
browser_console_logs                — получить логи консоли
```

## Пример автономного сценария

```
Ты — автономный тестер-агент. Запусти браузер, зарегистрируй нового 
пользователя (email: test_{{timestamp}}@example.com, пароль: Test123!), 
добавь товар в корзину, оформи заказ. Проверь что нет ошибок в консоли 
и 500 на API. Сохрани скриншот каждого шага.
```

Агент сам:
1. Открывает `https://promelectron-test.aidrivencode.ru`
2. Ищет форму регистрации (через data-testid или текст кнопки)
3. Заполняет поля
4. Жмёт "Зарегистрироваться"
5. Проверяет что URL изменился на `/`
6. Идёт в каталог, кликает первый товар
7. Добавляет в корзину
8. Проверяет toast-уведомление
9. Идёт в корзину → оформление
10. Сохраняет отчёт

## Файлы проекта

| Файл | Назначение |
|---|---|
| `tests/agent/personas.js` | Роли и разрешения |
| `tests/agent/scenarios.js` | Библиотека сценариев |
| `tests/agent/agent.js` | Автономный loop (MCP → действие → проверка → отчёт) |
| `tests/agent/reports/` | Скриншоты + JSON отчёты |
| `e2e/*.spec.js` | Существующие Playwright тесты (используют как базу) |

## Как запустить

### Через MCP (ручной режим)
```bash
# Уже настроено в .mcp.json
npx @playwright/mcp@latest --headless
```

### Через автономного агента
```bash
node tests/agent/agent.js --persona=user --scenario=fullPurchaseFlow
node tests/agent/agent.js --persona=admin --scenario=adminCategoryManagement
node tests/agent/agent.js --persona=supplier --scenario=supplierAddProduct
```

### Через CI (GitHub Actions)
```yaml
- name: Autonomous Agent Testing
  run: |
    npx playwright install chromium
    node tests/agent/agent.js --persona=all --report=json
```

## Генерация баг-репорта

Агент сохраняет:
```json
{
  "id": "bug-2026-05-20-001",
  "severity": "critical",
  "title": "Регистрация возвращает 500",
  "persona": "user",
  "steps": [
    "Открыть /register",
    "Заполнить email: test_123@test.com",
    "Заполнить пароль: Test123!",
    "Нажать 'Зарегистрироваться'"
  ],
  "expected": "Редирект на /, токен в localStorage",
  "actual": "Toast: 'Ошибка регистрации. Попробуйте позже.'",
  "api_response": { "status": 500, "body": "Internal Server Error" },
  "screenshots": ["step-1.png", "step-4-error.png"],
  "console_errors": ["GET /api/v1/register 500"],
  "timestamp": "2026-05-20T02:54:20Z"
}
```

## Прокачка агента

Чтобы агент стал умнее, добавь:

1. **Memory** — `memory` MCP сервер уже подключён. Агент запоминает созданные аккаунты и товары между сессиями.

2. **Sequential Thinking** — `sequential-thinking` MCP помогает агенту планировать сложные сценарии (например, "сначала создать категорию как админ, потом добавить товар как поставщик").

3. **Vision** — скриншоты анализируются через vision-capable модель для обнаружения UI багов.

4. **API Testing** — параллельно с UI проверять API endpoints (`curl` / `fetch`).

5. **State Machine** — переходы между состояниями: `anonymous` → `registered` → `with_cart` → `ordered`.
