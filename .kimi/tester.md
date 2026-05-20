# 🤖 Autonomous Tester Agent v2

## Что умеет

Агент выполняет **полное автономное тестирование** e-commerce приложения:

### 🔬 Режимы тестирования
- **Scenarios** — 20+ сценариев для user/admin/supplier/security/performance/accessibility/responsive/fuzz/cross-role
- **Discovery** — автономное исследование сайта
- **Performance** — Core Web Vitals (LCP, CLS, FCP, TTFB)
- **Accessibility** — a11y проверки (alt, labels, headings, landmarks, lang)
- **Responsive** — тестирование mobile/tablet/desktop viewports
- **Security** — unauthorized access, form validation, XSS/SQL injection, API authorization
- **Fuzz** — случайные данные, edge cases
- **Cross-role** — сквозные сценарии через несколько ролей

### 🧠 Интеллект
- Реальный браузер через Playwright MCP (23 инструмента)
- Text-based селекторы (`text=Войти`) + fallback на data-testid/CSS
- Retry logic (3 попытки с разными селекторами)
- Vision Analyzer — определение типа страницы по snapshot
- Персистентная память между запусками
- API + UI dual testing

### 📊 Отчёты
- JSON, HTML, Markdown
- Скриншоты каждого шага
- Performance метрики
- Accessibility аудит
- Историческая статистика

## Архитектура

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Persona    │────▶│  Scenario    │────▶│  MCP Bridge  │
│  (роль +     │     │  (что делать)│     │  (Playwright │
│  тест-данные)│     │              │     │   via stdio) │
└──────────────┘     └──────────────┘     └──────────────┘
        │                                          │
        │         ┌──────────────┐                 │
        └────────▶│   Vision     │◀────────────────┘
                  │  Analyzer    │
                  └──────────────┘
                          │
                   ┌──────────────┐
                   │  API Client  │
                   │  (HTTP fetch)│
                   └──────────────┘
                          │
                   ┌──────────────┐
                   │  State Machine│
                   │  (memory.json)│
                   └──────────────┘
                          │
                   ┌──────────────┐
                   │  Bug Report  │
                   │  (JSON/HTML/ │
                   │   Markdown)  │
                   └──────────────┘
```

## Компоненты

### MCP Bridge (`tests/agent/mcp-bridge.js`)
- `@modelcontextprotocol/sdk` + `StdioClientTransport`
- Запускает `npx @playwright/mcp@latest --headless`
- 23 инструмента: navigate, click, fill, screenshot, evaluate, console, tabs, etc.
- Поддерживает text-based (`text=Войти`), ref-based (`e28`), CSS селекторы
- Автоматический парсинг результатов evaluate (JSON, boolean, number, string)

### Vision Analyzer (`tests/agent/vision.js`)
- Анализ UI через snapshot + accessibility tree
- Определение типа страницы (login, product_list, cart, error, etc.)
- Поиск элементов по тексту для fallback селекторов
- Поддержка OpenAI Vision API (опционально, через `OPENAI_API_KEY`)

### State Machine (`tests/agent/state.js`)
- Аккаунты всех ролей с токенами
- Созданные сущности (товары, категории, заказы)
- Найденные баги с дедупликацией
- История сессий
- Learnings — что агент узнал о сайте

### API Client (`tests/agent/api-client.js`)
- Полное покрытие backend API: auth, users, products, categories, cart, orders, favorites, reviews, payments, notifications, delivery methods, admin
- Валидация ответов (status, fields, array length, duration)
- Логирование всех запросов

### Autonomous Agent (`tests/agent/autonomous-agent.js`)
- Execution engine с retry и fallback
- Assertion engine: url, element, text, toast, evaluate
- API validation после каждого сценария
- Autonomous discovery mode
- Performance testing (Core Web Vitals)
- Accessibility testing
- Responsive testing
- Cross-role scenario support

### Runner (`tests/agent/runner.js`)
- CLI с поддержкой всех режимов
- Отчёты в JSON/HTML/Markdown
- Историческая статистика

## Роли (Personas)

```js
user       — Обычный покупатель (регистрация, покупка, поиск, корзина, заказы)
admin      — Администратор (категории, пользователи, заказы, статистика, доставка)
supplier   — Поставщик (товары, заказы, профиль)
security   — Security Auditor (доступы, валидация, инъекции, API auth)
performance — Performance Engineer (LCP, CLS, FCP, TTFB, API response time)
crossrole  — Сквозные сценарии (admin → supplier → user)
fuzz       — Случайные данные, edge cases
accessibility — A11y проверки
responsive  — Mobile/tablet/desktop breakpoints
```

## Сценарии

### User (8 сценариев)
- `fullPurchaseFlow` — Регистрация → каталог → товар → корзина → checkout
- `searchAndFilter` — Поиск, фильтры, сортировка
- `favoritesFlow` — Избранное
- `userProfileFlow` — Профиль пользователя
- `userOrdersFlow` — Заказы
- `userReviewFlow` — Отзывы
- `cartManagementFlow` — Корзина (изменение количества, удаление)

### Admin (5 сценариев)
- `adminCategoryManagement` — Управление категориями
- `adminUserManagement` — Управление пользователями
- `adminOrderManagement` — Управление заказами
- `adminDashboardStats` — Статистика дашборда
- `adminDeliveryMethods` — Способы доставки

### Supplier (4 сценария)
- `supplierAddProduct` — Добавление товара
- `supplierEditProduct` — Редактирование товара
- `supplierDeleteProduct` — Удаление товара
- `supplierOrdersFlow` — Заказы поставщика

### Security (4 сценария)
- `unauthorizedAccess` — Проверка доступов
- `formValidation` — Валидация форм
- `injectionChecks` — XSS/SQL injection
- `apiAuthorization` — API авторизация

### Performance (3 сценария)
- `layoutStability` — Layout shift
- `coreWebVitals` — LCP, CLS, FCP, TTFB
- `apiPerformance` — API response time

### Cross-role (1 сценарий)
- `endToEndPurchase` — Admin → Supplier → User

### Fuzz (2 сценария)
- `fuzzRegistration` — Регистрация с edge case данными
- `fuzzProductCreation` — Товар с extreme ценами

### Accessibility (1 сценарий)
- `accessibilityCheck` — A11y аудит

### Responsive (2 сценария)
- `responsiveMobile` — Мобильный viewport
- `responsiveTablet` — Планшетный viewport

## Как запускать

### Локально

```bash
# Сценарии
npm run agent -- --persona=user --scenario=fullPurchaseFlow
npm run agent:user
npm run agent:admin
npm run agent:supplier
npm run agent:security
npm run agent:all

# Специальные режимы
npm run agent:performance
npm run agent:accessibility
npm run agent:responsive
npm run agent:crossrole
npm run agent:fuzz

# Discovery
npm run agent:discover

# Отладка
npm run agent -- --persona=user --headed --debug

# Кастомные URL
npm run agent -- --base-url=http://localhost:5173 --api-url=http://localhost:8000
```

### Окружение

```bash
export TEST_BASE_URL=https://promelectron-test.aidrivencode.ru
export TEST_API_URL=https://api.promelectron-test.aidrivencode.ru
export OPENAI_API_KEY=sk-...          # для vision model (опционально)
export VISION_PROVIDER=openai          # или heuristic (default)
export AGENT_STATE_FILE=./tests/agent/.agent-state.json
```

### CI/CD (GitHub Actions)

Уже интегрировано в `.github/workflows/deploy.yml`:

```yaml
- name: Run Autonomous Agent (User scenarios)
  run: npm run agent:user

- name: Run Performance Tests
  run: npm run agent:performance

- name: Run Accessibility Tests
  run: npm run agent:accessibility

- name: Run Security Tests
  run: npm run agent:security

- name: Upload agent reports
  uses: actions/upload-artifact@v4
  with:
    name: agent-reports
    path: tests/agent/reports/
```

## Файлы проекта

| Файл | Строки | Назначение |
|---|---|---|
| `tests/agent/agent.js` | 77 | Entry point (CLI) |
| `tests/agent/runner.js` | 204 | Test runner + отчёты |
| `tests/agent/autonomous-agent.js` | 506 | Execution engine |
| `tests/agent/mcp-bridge.js` | 272 | MCP SDK + Playwright bridge |
| `tests/agent/vision.js` | 253 | UI анализ (snapshot + vision) |
| `tests/agent/state.js` | 197 | Память агента |
| `tests/agent/api-client.js` | 214 | HTTP API клиент |
| `tests/agent/personas.js` | 141 | Роли и разрешения |
| `tests/agent/scenarios.js` | 158 | Библиотека сценариев |

## Баг-репорт

Агент автоматически сохраняет:
```json
{
  "id": "bug-1779250999160-7xhl",
  "severity": "critical|major|minor",
  "message": "URL mismatch: ...",
  "persona": "user",
  "scenario": "fullPurchaseFlow",
  "step": 7,
  "url": "https://...",
  "timestamp": "2026-05-20T04:23:19.160Z"
}
```

## Прокачка агента

1. **Vision Model** — подключить `OPENAI_API_KEY` для анализа скриншотов через GPT-4o
2. **Sequential Thinking** — MCP сервер уже подключён в `.mcp.json`
3. **Memory** — `memory` MCP сервер уже подключён
4. **Filesystem** — `filesystem` MCP сервер уже подключён
5. **New Scenarios** — добавлять новые сценарии в `scenarios.js`
6. **Custom Selectors** — добавлять fallback селекторы в `FALLBACK_SELECTORS`
