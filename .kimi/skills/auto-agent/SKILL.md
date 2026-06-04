---
name: auto-agent
description: Автоматический выбор агента по задаче. Анализирует описание задачи, определяет роль (backend-dev, frontend-dev, devops, e2e-tester и т.д.), собирает контекст из PROJECT_CONTEXT.md, BACKLOG.md, BLOCKERS.md и начинает работу без ручного выбора роли.
argument-hint: "<описание задачи>"
disable-model-invocation: false
---

# Auto-Agent — Автоматический роутер задач

> **Цель:** Пользователь просто описывает задачу. Система сама определяет, какой агент нужен, собирает контекст и начинает работу.

## Как работает роутинг

### Шаг 1: Анализ задачи
Прочитай описание задачи от пользователя. Определи роль по ключевым словам:

| Роль | Ключевые слова |
|------|---------------|
| `orchestrator` | Любые — система сама определит роли | Авто-определение + делегирование через Agent tool |
| `backend-dev` | API, endpoint, backend, бэк, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, БД, таблица, webhook, JWT, OAuth (backend), payment, заказ, order, корзина (API), auth (backend), admin (API) |
| `frontend-dev` | frontend, фронт, Vue, component, страница, page, view, Pinia, store, composable, UI, UX, форма, form, адаптив, CSS, HTML, Axios, router, localStorage, корзина (UI), login (UI), checkout (UI) |
| `devops` | Docker, K8s, Kubernetes, Helm, nginx, CI/CD, deploy, деплой, инфраструктура, infra, SSL, VPN, backup, Sentry, monitoring, pod, container, Harbor, GitHub Actions, workflow, secret, config |
| `e2e-tester` | E2E, Playwright, тест сценарий, test scenario, browser, click, end-to-end, regression, регресс, spec |
| `code-reviewer` | review, ревью, code review, проверь код, findings, quality, качество кода |
| `security-reviewer` | security, аудит, audit, уязвимость, vulnerability, SQL injection, XSS, CSRF |
| `project-manager` | roadmap, план, спринт, sprint, приоритет, prioritize, бэклог, backlog, оцени, estimate, planning |

**Правило:** Если ключевые слова смешанные (например, "Сделай API и фронт"):
- **В orchestrator-режиме:** запусти `.agent/ORCHESTRATOR_PROMPT.md` — он сам разберётся
- **В диспетчер-режиме:** выбери **основную** роль (обычно backend-dev), а фронтенд сделай отдельной задачей позже

### Шаг 2: Чтение контекста

Обязательно прочитай перед работой:
1. `PROJECT_CONTEXT.md` — стек, статус фич, блокеры, API Inventory, Frontend Map
2. `.agent/BACKLOG.md` — текущий спринт, есть ли уже такая задача
3. `.agent/BLOCKERS.md` — нет ли блокеров, которые помешают
4. `.agent/SESSION_LOG.md` — что делалось в последних сессиях
5. `.kimi/agents/<ROLE>.md` — правила конкретного агента

### Шаг 3: Выполнение

Следуй workflow выбранного агента:
- **backend-dev:** model → schema → service → route → tests
- **frontend-dev:** component → API integration → tests
- **devops:** Helm/Docker → CI/CD → verify deploy
- **e2e-tester:** scenario → selectors → test → run

### Шаг 4: Отчёт

После выполнения:
1. Допиши в `.agent/SESSION_LOG.md`
2. Обнови `BACKLOG.md` если задача из спринта
3. Обнови `PROJECT_CONTEXT.md` если изменилась архитектура или появилась новая фича

## Пример использования

Пользователь: «Добавь промокоды в корзину»

1. **Роутинг:** «корзина» + «добавь» → `backend-dev` (сначала API, потом frontend)
2. **Контекст:** Читаю PROJECT_CONTEXT.md — корзина работает, ЮKassa в процессе
3. **План:**
   - Model: PromoCode (code, discount_type, amount, limit, expires_at)
   - Schema: PromoCodeCreate, PromoCodeOut
   - Service: PromoCodeService
   - Route: POST /cart/apply-promo/, GET /admin/promo-codes/
   - Tests: test_promo_codes.py
4. **Отчёт:** Дописал в SESSION_LOG.md, обновил BACKLOG.md

## Ограничение: смена роли в рамках одной сессии

> ⚠️ В рамках одной сессии Kimi CLI LLM может "залипнуть" в предыдущей роли. Если последние 5+ сообщений были в роли backend-dev, а новая задача — frontend, модель может продолжить как backend-dev.
>
> **Решения (по надёжности):**
> 1. **Orchestrator:** Начни сессию с `.agent/ORCHESTRATOR_PROMPT.md` — изолированные Agent'ы, никаких залипаний
> 2. **Диспетчер:** Начни сессию с `.kimi/agents/dispatcher.md` — он сбрасывает роль при каждом запросе
> 3. **Скрипт:** `make auto MSG="..."` или `make ask MSG="..."` для каждой задачи
> 4. Новая сессия Kimi CLI
> 5. Явно указать роль: `Роль: frontend-dev. Задача: ...`

## Анти-паттерны

- ❌ Не пытайся сделать backend + frontend + devops в одной задаче
- ❌ Не игнорируй блокеры — если BLK-002 (Celery не работает) мешает email-нотификациям, скажи об этом
- ❌ Не угадывай контекст — всегда читай файлы
