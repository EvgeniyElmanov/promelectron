# ROUTER — маршрутизация агентов для Promelectron

> Опиши задачу — система выберет нужного агента, соберёт контекст и начнёт работать.

## Языковое правило

Когда пользователь общается на русском языке, основной агент и все субагенты должны рассуждать и думать на русском. Родительский агент должен явно сообщать субагентам, что исходный пользователь общается на русском, чтобы они тоже рассуждали на русском. Финальные ответы пользователю должны быть на русском языке, при этом код, команды, идентификаторы, пути к файлам и технические термины остаются в оригинальном виде.

## Быстрый старт

### Вариант 1: Workflow-навыки (рекомендуется)

```
/skill:implement "Add promo codes to cart"     # полный цикл разработки фичи
/skill:fix "Race condition in cart add"        # workflow исправления бага
/skill:deploy test                             # деплой через GitHub Actions
/skill:review                                  # код-ревью текущих изменений
/skill:context-sync                            # обновить файлы контекста проекта
```

### Вариант 2: Фиксированная роль (когда знаешь, кто нужен)

```
Role: backend-dev. Task: add email validation to registration.
```

### Вариант 3: Диспетчер (ad-hoc задачи)

```
Load `/skill:dispatcher` or read `.kimi-code/skills/dispatcher/SKILL.md` and follow its instructions strictly.
Task: Create an API for promo codes.
```

## Как работает маршрутизация

| Роль | Ключевые слова в задаче | Когда выбирать |
|------|-------------------------|----------------|
| `implement` | Новая фича, API, страница, компонент | Полный цикл: architect → dev → review → QA |
| `fix` | Баг, ошибка, краш, не работает | Анализ → воспроизведение → фикс → тест |
| `deploy` | Деплой, релиз, продакшн | GitHub Actions → наблюдение → E2E smoke test |
| `backend-dev` | API, endpoint, backend, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, DB, table, webhook, JWT, OAuth (backend), payment, order, cart (API), auth (backend), admin (API) | Только backend-задачи |
| `frontend-dev` | frontend, Vue, component, page, view, Pinia, store, composable, UI, UX, form, responsive, CSS, Axios, router, localStorage, cart (UI), login (UI), checkout (UI) | Только frontend-задачи |
| `devops` | Docker, K8s, Kubernetes, Helm, nginx, CI/CD, deploy, infra, SSL, VPN, backup, Sentry, monitoring, pod, container, GitHub Actions, workflow, secret, config | Инфраструктурные задачи |
| `e2e-tester` | E2E, Playwright, test scenario, browser, click, end-to-end, regression, spec | E2E-сценарии |
| `code-reviewer` | review, code review, findings, quality | Код-ревью |
| `security-reviewer` | security, audit, vulnerability, SQL injection, XSS, CSRF | Security-аудит |
| `project-manager` | roadmap, plan, sprint, prioritize, backlog, estimate, planning | Планирование |
| `qa` | test, acceptance criteria, full check, qa | Полная пирамида тестирования |
| `integration-dev` | dev environment, services won't start, ports, health check | Операции локального окружения |

**Смешанные задачи** (например, "API и фронтенд для промокодов"):
1. `/skill:implement` выбирает основную роль и может запускать backend + frontend последовательно.
2. Для ad-hoc смешанной работы используй dispatcher.

## Архитектура

```
Пользователь описывает задачу
       │
       ▼
┌─────────────────────────────┐
│  /skill:implement или /skill:fix skill   │
│  (в .kimi-code/skills/)     │
└─────────────┬───────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  ┌─────────┐  ┌──────────┐
  │ Читает  │  │ Читает   │
  │PROJECT_ │  │BACKLOG,  │
  │CONTEXT  │  │BLOCKERS  │
  └────┬────┘  └────┬─────┘
       │            │
       └─────┬──────┘
             ▼
  ┌──────────────────────┐
  │ Создаёт субагента    │
  │ (architect/dev/QA)   │
  └──────────┬───────────┘
             ▼
  ┌──────────────────────┐
  │ Пишет артефакты      │
  │ (spec, findings)     │
  └──────────────────────┘
```

## Файлы

| Файл | Назначение |
|------|------------|
| `.kimi-code/skills/promelectron/SKILL.md` | Главный skill с реестром агентов и золотыми правилами |
| `.kimi-code/skills/implement/SKILL.md` | Полный цикл разработки фичи |
| `.kimi-code/skills/fix/SKILL.md` | Workflow исправления бага |
| `.kimi-code/skills/review/SKILL.md` | Workflow код-ревью |
| `.kimi-code/skills/deploy/SKILL.md` | Workflow деплоя |
| `.kimi-code/skills/context-sync/SKILL.md` | Синхронизация контекста |
| `.kimi-code/skills/plan-maintainer/SKILL.md` | Поддержка бэклога/планирования |
| `.kimi-code/skills/<role>/SKILL.md` | Инструкции ролей (flat Kimi skills) |
| `.kimi-code/rules/*.md` | Общие конвенции (reference markdown) |
| `PROJECT_CONTEXT.md` | Единый источник истины |
| `docs/backlog.md` | Текущий спринт |
| `docs/blockers.md` | Активные блокеры |
| `docs/journal/session-log.md` | Лог сессий |

## Добавление новой роли

1. Создать новый flat skill в `.kimi-code/skills/<role>/SKILL.md`
2. Добавить роль в `.kimi-code/skills/promelectron/SKILL.md` (мастер-индекс)
3. Добавить ключевые слова в `.kimi-code/skills/dispatcher/SKILL.md`
4. Обновить `docs/guides/agent-routing.md` и `docs/guides/session-start.md`
5. Если роль участвует в `/skill:implement`, обновить `.kimi-code/skills/implement/SKILL.md`
