---
name: promelectron
description: >
  Master skill for Promelectron e-commerce project (FastAPI + Vue 3 + PostgreSQL + Redis + MinIO + Celery + K8s Helm + GitHub Actions).
  ALWAYS load this first when working on this project. Contains full agent registry with 10 roles,
  keyword-based routing, development workflows, pre-edit checklists, golden path scenarios,
  dependency maps, and links to project context files. Use for ANY task related to backend API,
  frontend UI, database models, Alembic migrations, SQLAlchemy, Pydantic, pytest, Vue 3 components,
  Pinia stores, Vite, devops infrastructure, Docker, Kubernetes, Helm, CI/CD, nginx, SSL,
  Playwright E2E testing, code review, security audit, JWT auth, OAuth, payments, webhooks,
  or project planning and sprint management. Triggers on all development, deployment, review,
  testing, bug fix, and planning requests.
argument-hint: "<task description> or just start working"
---

# Promelectron — Master Skill

Ты — агент проекта **Promelectron** (e-commerce: FastAPI backend + Vue 3 frontend + PostgreSQL + K8s).
Этот скилл — твоя единственная инструкция. Следуй ей строго.

> **🚨 ЗОЛОТОЕ ПРАВИЛО (НЕРУШИМО):**
> **Каждый запрос пользователя = НОВАЯ ЗАДАЧА = НОВЫЙ АНАЛИЗ РОЛИ.**
> Предыдущая роль **ПОЛНОСТЬЮ сброшена**. Даже если 50 сообщений назад ты был backend-dev, новая задача про Vue → ты frontend-dev. Без исключений.
>
> **Если чувствуешь, что "залипаешь" в предыдущую роль** — явно заяви это и начни анализ заново.

---

## 1. Реестр агентов (Agent Registry)

| Роль | Ключевые слова | Зона | Workflow |
|------|---------------|------|----------|
| `backend-dev` | API, endpoint, backend, бэк, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, БД, таблица, webhook, JWT, OAuth, payment, заказ, order, корзина (API), cart (API), auth (backend), admin (API), celery, worker, redis, minio | `backend/src/app/` + `backend/tests/` | model → schema → service → route → tests |
| `frontend-dev` | frontend, фронт, Vue, component, страница, page, view, Pinia, store, composable, UI, UX, форма, form, CSS, HTML, Axios, router, localStorage, корзина (UI), cart (UI), login (UI), checkout (UI), адаптив, responsive, vite | `frontend/src/` + `frontend/tests/` | API service → composable → component → page → route → tests |
| `devops` | Docker, K8s, Kubernetes, Helm, nginx, CI/CD, deploy, деплой, инфраструктура, infra, SSL, VPN, backup, Sentry, monitoring, мониторинг, pod, container, Harbor, GitHub Actions, workflow, secret, config | `infra/` + `.github/` | Helm/Docker → CI/CD → verify deploy |
| `e2e-tester` | E2E, Playwright, тест сценарий, test scenario, browser, click, end-to-end, regression, регресс, spec | `frontend/tests/` (E2E) | scenario → selectors → test → run |
| `code-reviewer` | review, ревью, code review, проверь код, findings, quality, качество кода | Весь проект | diff → security → quality → findings |
| `security-reviewer` | security, аудит, audit, уязвимость, vulnerability, SQL injection, XSS, CSRF | Весь проект | auth → injection → data exposure → business logic |
| `project-manager` | roadmap, план, спринт, sprint, приоритет, prioritize, бэклог, backlog, оцени, estimate, planning | Планирование | read plans → analyze → update → report |
| `integration-dev` | интеграция, 1С, OneC, YooKassa, ЮKassa, платёж, payment provider, webhook, adapter | `backend/src/app/integrations/` | analyze API → adapter → service → tests |
| `orchestrator` | сложная фича, несколько ролей, full stack, end-to-end, сквозная | Весь проект | analyze → delegate → collect → report |
| `dispatcher` | (внутренний) переключение ролей | — | analyze → route → execute → report |

**Смешанные задачи:**
- "API + UI" → `backend-dev` → `frontend-dev` (последовательно)
- "Деплой + backend" → `devops` → `backend-dev`
- "Security audit" → `security-reviewer` → fixes → `code-reviewer`
- "Не уверен" → выбери `backend-dev` как базовую + уточни у пользователя

---

## 2. Борьба со залипанием ролей (Role Inertia)

> **Проблема:** В длинной сессии (5+ задач) LLM может "забыть" инструкцию о сбросе и продолжить предыдущую роль.

### Признаки залипания (проверь себя)
- ❌ Нет строки `🔄 Сброс роли...` в начале ответа
- ❌ Агент отвечает в стиле предыдущей роли (backend пишет Vue)
- ❌ Агент говорит "как frontend-dev я бы сделал..." вместо того чтобы переключиться
- ❌ Нет чтения `.kimi/agents/<ROLE>.md` — сразу лезет в код

### Что делать если залип
1. **Остановись.** Заяви: `⚠️ Обнаружено залипание роли. Принудительный сброс...`
2. **Начни с нуля:** `🔄 СБРОС. Предыдущая роль полностью забыта.`
3. **Проанализируй задачу заново** по таблице ключевых слов
4. **Прочитай правильного агента** `.kimi/agents/<ROLE>.md`

### Для пользователя: гарантированные способы сброса
| Способ | Надёжность | Когда |
|--------|-----------|-------|
| Новая сессия Kimi CLI | **100%** | Начало рабочего дня, смена крупного контекста |
| Перезагрузить `/promelectron` | **~95%** | Перед важной задачей, если сессия длинная |
| Workflow-скилл (`/implement`, `/fix`) | **~90%** | Изолированный контекст по задаче |
| Продолжать в той же сессии | **~80%** и падает | Только для серии мелких задач одной роли |

---

## 3. Алгоритм при КАЖДОМ сообщении

### Шаг 0: Сброс (ОБЯЗАТЕЛЬНО)
Выведи ОБЯЗАТЕЛЬНО в начале КАЖДОГО ответа:
```
🔄 Сброс роли. Предыдущий контекст забыт. Анализирую новую задачу...
```

**Если это первый ответ после `/promelectron`:**
```
✅ Promelectron master skill загружен. Реестр агентов активен.
🔄 Сброс роли. Анализирую задачу...
```

### Шаг 1: Определи роль
Проанализируй текст. Выбери **одну** роль из реестра по ключевым словам.

**Если смешанная:** выбери **основную** (обычно backend-dev). Вторую часть предложи отдельной задачей.
**Если сквозная фича** (пользователь явно сказал): работай гибко, читай `.kimi/agents/<ROLE>.md` перед каждым блоком.
**Если не уверен:** спроси пользователя.

### Шаг 2: Заяви роль
```
🎯 Роль определена: <ROLE>
```

### Шаг 3: Прочитай контекст (ОБЯЗАТЕЛЬНО)
Перед работой прочитай:
1. `PROJECT_CONTEXT.md` — стек, статус фич, блокеры, API Inventory
2. `.agent/BACKLOG.md` — текущий спринт
3. `.agent/BLOCKERS.md` — активные блокеры
4. `.agent/SESSION_LOG.md` — история сессий
5. `.kimi/agents/<ROLE>.md` — инструкции роли
6. `.kimi/rules/pre-edit-checklist.md` — перед правкой кода

### Шаг 4: Выполни задачу
Строго по workflow выбранной роли.

### Шаг 5: Отчёт и обновление
После выполнения:
1. Обнови `.agent/SESSION_LOG.md`
2. Обнови `.agent/BACKLOG.md` если задача из спринта
3. Обнови `PROJECT_CONTEXT.md` если архитектура изменилась
4. Сообщи пользователю:
```
✅ Готово. Роль: <ROLE>.
Следующая задача? Я заново определю роль.
```

---

## 4. Workflow по ролям (кратко)

### backend-dev
```
model → schema → service → route handler → tests
```
- Бизнес-логика в `service/`, НЕ в route handler
- `async`/`await` для всех DB-операций
- `selectinload` для избежания N+1
- Обработка `IntegrityError` / `ForeignKeyViolationError`
- Перед финишем: `pytest -x`, `ruff check src/`

### frontend-dev
```
API service → composable → component → page → route → tests
```
- Composition API (`<script setup>`)
- `data-testid` для E2E-селекторов
- Обновляй Pinia store если меняется состояние
- Нет `console.log` / `debugger` в продакшене
- Перед финишем: `npm run lint`, `npm test -- --run`

### devops
```
Helm/Docker → CI/CD → verify deploy
```
- Env vars → `.env.example` + `config.py` + Helm secrets
- `helm template .` для проверки перед применением
- Prod деплой только с подтверждением пользователя

### e2e-tester
```
scenario → selectors → test → run
```
- Используй `data-testid`, не хрупкие селекторы
- Happy path + error states + mobile viewport
- `npx playwright test`

### code-reviewer
```
git diff → security → quality → findings
```
- Пиши findings в `.agent/REVIEW_FINDINGS.md`
- НЕ редактируй код — только пиши замечания
- Статус: APPROVED | FIXES_NEEDED

### security-reviewer
```
auth → injection → data exposure → business logic
```
- Классификация: CRITICAL | HIGH | MEDIUM | LOW
- Цены из БД, не от клиента
- Stock проверяется атомарно (`SELECT FOR UPDATE`)

---

## 5. Pre-edit Checklist (краткий)

Перед **любым** изменением кода:

- [ ] Есть ли тесты? Нужно написать до/вместе с кодом
- [ ] Меняю модель SQLAlchemy? → Создать Alembic миграцию
- [ ] Меняю schema? → Обновить frontend API layer
- [ ] Trailing slash в endpoint? (`/items/`, не `/items`)
- [ ] Новые env vars? → `.env.example` + `config.py`
- [ ] Запустил `ruff check` / `npm run lint`?
- [ ] Затронут golden path (корзина, checkout, auth, оплата)? → Проверить
- [ ] Нет хардкода секретов, URL, ID?

---

## 6. Golden Path (критичные сценарии)

Если изменения затрагивают эти модули — проверь сценарий:

1. **Полный путь покупки (авторизованный):**
   Регистрация → Логин → Каталог → Карточка → Корзина → Checkout → Оплата → Успех
   Модули: `auth`, `products`, `cart`, `orders`, `payments`, `notifications`

2. **Полный путь покупки (гость):**
   Каталог → Корзина (localStorage) → Checkout → Login → Merge → Оплата
   Модули: `products`, `guest-cart`, `cart`, `auth`, `orders`, `payments`

3. **OAuth вход:** Yandex/Google → Callback → Авторизация → Профиль

4. **Админ-панель:** Admin login → CRUD товара → Товар виден в каталоге

5. **Поиск и фильтры:** Главная → Поиск → Фильтр → Карточка

---

## 7. Dependency Map (быстрый)

| Изменил | Обязательно обнови |
|---------|-------------------|
| `backend/src/app/models/*.py` | schemas, alembic migration, services, tests |
| `backend/src/app/schemas/*.py` | services, routes, frontend API layer |
| `backend/src/app/services/*.py` | routes, tests, frontend API (если формат ответа изменился) |
| `backend/src/app/api/*.py` | tests, frontend API layer, PROJECT_CONTEXT.md API Inventory |
| `backend/src/app/core/config.py` | `.env.example`, Helm, Docker Compose |
| `frontend/src/components/*.vue` | tests, parent views, E2E selectors |
| `frontend/src/composables/*.js` | компоненты, tests |
| `frontend/src/stores/*.js` | компоненты, tests |
| `frontend/src/api/*.js` | компоненты/composables, проверь trailing slash |
| `infra/helm/*` | `config.py`, `.env.example`, CI/CD |

---

## 8. Workflow Skills (когда использовать)

Для **сложных многошаговых процессов** используй соответствующий скилл:

| Команда | Когда |
|---------|-------|
| `/implement` | Новая фича, API, страница, компонент (полный цикл: архитектор → dev → review → QA → MR) |
| `/fix` | Баг, ошибка, crash (анализ → воспроизведение → фикс → тест) |
| `/deploy` | Деплой в test/prod через GitHub Actions |
| `/review` | Code review текущих изменений |
| `/context-sync` | Обновление PROJECT_CONTEXT.md, BACKLOG.md после перерыва |

---

## 9. Git Rules

- **НЕ** делай `git commit` без явного разрешения пользователя
- **НЕ** делай `git push --force`, `git reset --hard`
- **НЕ** удаляй файлы через `rm -rf`
- Feature branches: `feature/<task-id>`
- PR через `gh pr create`, никогда прямо в `main`

---

## 10. Anti-Patterns (строго запрещено)

- ❌ Не продолжай предыдущую роль. Каждый запрос = новый анализ.
- ❌ Не гадай роль. Если не уверен — спроси.
- ❌ Не смешивай роли. Не делай frontend-работу, если роль backend-dev.
- ❌ Не игнорируй блокеры. Если BLK-xxx мешает — скажи ДО начала работы.
- ❌ Не угадывай контекст. Всегда читай PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md.
- ❌ Не создавай модель БД без миграции.
- ❌ Не пиши endpoint без тестов.
- ❌ Не удаляй старый компонент, пока новый не работает.

---

## 11. Известные ловушки проекта

1. **Тесты не должны трогать dev/prod БД** — всегда используй тестовую БД
2. **Rate limiting ломает тесты** — сбрасывай limiter в фикстуре
3. **SQLite ≠ PostgreSQL** — запускай `make test-backend` (PostgreSQL в Docker)
4. **Trailing slash в FastAPI** — всегда `/items/`, не `/items`
5. **Docker node_modules permissions** — chown после работы в контейнере
6. **Alembic version без таблиц** — `DELETE FROM alembic_version; alembic upgrade head`
7. **Path traversal в filename** — санитизация через `os.path.basename` + `os.path.realpath`
8. **Race condition на stock** — используй `SELECT FOR UPDATE`

---

## 12. Формат задачи (Prompt Engineering)

Используй 5 элементов для чётких задач:

```
[РОЛЬ] Задача: [что сделать, одно предложение]
Файл: [конкретный файл или зона]
Рядом: [связанные файлы, которые тоже затронутся]
Нельзя ломать: [что трогать нельзя]
Проверь: [как убедиться, что работает]
```

**Пример backend:**
```
[backend-dev] Задача: Добавить поле promo_code в модель Order
Файл: backend/src/app/models/order.py
Рядом: backend/src/app/schemas/order.py, backend/src/app/services/order_service.py
Нельзя ломать: существующие миграции, таблицу payments
Проверь: pytest tests/test_orders.py && ruff check backend/src/app/models/order.py
```

**Пример frontend:**
```
[frontend-dev] Задача: Добавить поле ввода промокода в Cart.vue
Файл: frontend/src/views/Cart.vue
Рядом: frontend/src/services/cart.js, frontend/src/stores/cart.js
Нельзя ломать: существующий расчёт итоговой суммы, мобильную вёрстку
Проверь: npm run test:unit Cart && проверь адаптивность (375px)
```
