# Rule: prompt-format

> Профессиональный подход: чем конкретнее задача — тем лучше результат. LLM не умеет догадываться.

## Правило: 5 элементов каждой задачи

Каждая задача, которую ты даёшь агенту, должна содержать:

```
[РОЛЬ] Задача: [что сделать, одно предложение]
Файл: [конкретный файл или зона]
Рядом: [связанные файлы, которые тоже затронутся]
Нельзя ломать: [что трогать нельзя]
Проверь: [как убедиться, что работает]
```

## Примеры по ролям

### Backend-dev

```
[backend-dev] Задача: Добавить поле promo_code в модель Order
Файл: backend/src/app/models/order.py
Рядом: backend/src/app/schemas/order.py, backend/src/app/services/order_service.py
Нельзя ломать: существующие миграции, таблицу payments
Проверь: pytest tests/test_orders.py && ruff check backend/src/app/models/order.py
```

### Frontend-dev

```
[frontend-dev] Задача: Добавить поле ввода промокода в Cart.vue
Файл: frontend/src/views/Cart.vue
Рядом: frontend/src/api/cart.js, frontend/src/composables/useCart.js
Нельзя ломать: существующий расчёт итоговой суммы, мобильную вёрстку
Проверь: make test-frontend && проверь адаптивность (375px)
```

### DevOps

```
[devops] Задача: Добавить YOOKASSA_SECRET_KEY в Helm secrets
Файл: infra/helm/templates/secrets.yaml
Рядом: infra/helm/values.yaml, .env.example
Нельзя ломать: существующие секреты (DATABASE_URL, JWT_SECRET)
Проверь: helm template . | grep -A5 yookassa && kubectl apply --dry-run=client -f infra/helm/templates/secrets.yaml
```

### E2E-tester

```
[e2e-tester] Задача: Написать тест применения промокода в корзине
Файл: frontend/e2e/cart.spec.js
Рядом: frontend/src/views/Cart.vue (data-testid для поля промокода)
Нельзя ломать: существующие тесты корзины
Проверь: npx playwright test frontend/e2e/cart.spec.js --headed
```

## Что НЕ делать

| ❌ Плохо | ✅ Хорошо |
|----------|----------|
| "Сделай API для промокодов" | "[backend-dev] Добавить POST /api/v1/promo/apply — принимает code, возвращает discount_amount" |
| "Почини баг в корзине" | "[backend-dev] Исправить race condition: при одновременном добавлении товара stock уходит в минус. Файл: services/cart.py, метод add_item" |
| "Настрой CI/CD" | "[devops] Добавить шаг проверки миграций в .github/workflows/deploy.yml перед деплоем" |
| "Напиши тест" | "[e2e-tester] Покрыть сценарий checkout → payment → success. URL: /checkout, /payment/success" |

## Почему это работает

1. **Роль** — убирает неопределённость. LLM сразу знает, в каком контексте думать.
2. **Файл** — сужает область поиска. Не "где-то в backend", а "вот этот файл".
3. **Рядом** — предотвращает "висячие" изменения (поменял API, но не обновил схему).
4. **Нельзя ломать** — защита от регрессий. Явно указывает границы.
5. **Проверь** — Definition of Done. Агент знает, когда задача считается выполненной.

## Как это автоматизировать

### Вариант A: Workflow skills (для полного цикла)

```
/skill:implement "Добавь промокоды в корзину"
```

Skill сам спроектирует, реализует, проверит и подготовит к merge.

### Вариант B: Руками (для сложных или частичных задач)

Ты сам формулируешь задачу по шаблону и вставляешь в Kimi CLI:

```
[backend-dev] Задача: Добавить поле promo_code в Order
Файл: backend/src/app/models/order.py
Рядом: backend/src/app/schemas/order.py, backend/src/app/services/order_service.py
Нельзя ломать: существующие миграции, таблицу payments
Проверь: pytest tests/test_orders.py && ruff check backend/src/app/models/order.py
```

### Вариант C: Диспетчер (для ad-hoc задач)

```
Role: backend-dev. Task: add email validation to registration.
```
