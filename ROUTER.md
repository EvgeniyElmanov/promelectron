# ROUTER — Автоматический выбор агента

> **Цель:** Ты просто описываешь задачу — система сама выбирает агента, собирает контекст и начинает работу.

---

## Быстрый старт

### Способ 1: Диспетчер (рекомендуется, только Kimi CLI)
```
Прочитай .agent/DISPATCHER_PROMPT.md и следуй инструкциям.
Задача: Создай API для промокодов
```
Диспетчер автоматически определит роль, сбросит предыдущую и переключится.

### Способ 2: Фиксированная роль (если знаешь, кто нужен)
```
Роль: backend-dev. Задача: Создай API для промокодов
```

### Способ 3: Bash-скрипт (если удобно через терминал)
```bash
make task MSG="Создай API для промокодов"
make ask MSG="Сделай страницу checkout"   # с гарантированным сбросом роли
```

---

## Как работает роутинг

| Роль | Ключевые слова в задаче | Когда выбирать |
|------|------------------------|--------------|
| `dispatcher` | Любые — диспетчер анализирует все задачи | Рекомендуется для сессий с задачами разных ролей |
| `backend-dev` | API, endpoint, backend, бэк, model, schema, service, route, migration, alembic, SQLAlchemy, FastAPI, pytest, БД, таблица, webhook, JWT, OAuth, payment, заказ, order, корзина (API), cart (API), auth (backend), admin (API) | Только backend задачи |
| `frontend-dev` | frontend, фронт, Vue, component, страница, page, view, Pinia, store, composable, UI, UX, форма, form, CSS, HTML, Axios, router, localStorage, корзина (UI), cart (UI), login (UI), checkout (UI) | Только frontend задачи |
| `devops` | Docker, K8s, Helm, nginx, CI/CD, deploy, деплой, инфраструктура, infra, SSL, VPN, backup, Sentry, monitoring, pod, container, Harbor, GitHub Actions, workflow, secret, config | Только devops задачи |
| `e2e-tester` | E2E, Playwright, тест сценарий, test scenario, browser, click, end-to-end, regression, регресс, spec | Только E2E задачи |
| `code-reviewer` | review, ревью, code review, проверь код, findings, quality | Только review |
| `security-reviewer` | security, аудит, audit, уязвимость, vulnerability, SQL injection, XSS, CSRF | Только security audit |
| `project-manager` | roadmap, план, спринт, sprint, приоритет, prioritize, бэклог, backlog, оцени, estimate, planning | Только планирование |

**Если задача смешанная** (например, «Сделай API и фронт для промокодов»):
1. Роутер выбирает **backend-dev** как основную роль
2. После завершения — создаёт отдельную задачу для `frontend-dev`

---

## Архитектура

```
Пользователь → описывает задачу
       │
       ▼
┌─────────────────────────────┐
│  scripts/kimi-task.sh       │
│  (keyword-based routing)    │
└─────────────┬───────────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
  ┌─────────┐  ┌──────────┐
  │Читает   │  │Читает    │
  │PROJECT_ │  │BACKLOG,  │
  │CONTEXT  │  │BLOCKERS  │
  └────┬────┘  └────┬─────┘
       │            │
       └─────┬──────┘
             ▼
  ┌──────────────────────┐
  │ Формирует полный     │
  │ промпт с контекстом  │
  └──────────┬───────────┘
             │
             ▼
  ┌──────────────────────┐
  │ Копирует в буфер     │
  │ (xclip / wl-copy)    │
  └──────────┬───────────┘
             │
             ▼
      Пользователь вставляет
      в Kimi CLI → Enter
```

---

## Файлы системы

| Файл | Назначение |
|------|-----------|
| `.agent/DISPATCHER_PROMPT.md` | **Главный файл.** Инструкции диспетчера для автопереключения ролей внутри Kimi CLI. |
| `.kimi/agents/dispatcher.md` | Универсальный диспетчер-агент. Альтернатива DISPATCHER_PROMPT.md. |
| `PROJECT_CONTEXT.md` | Единый источник контекста (читается агентами). |
| `.agent/BACKLOG.md` | Текущий спринт (читается агентами). |
| `.agent/BLOCKERS.md` | Блокеры (читаются агентами). |
| `.agent/SESSION_LOG.md` | Лог сессий (читается агентами). |
| `scripts/kimi-task.sh` | Shell-скрипт роутера (опционально, через терминал). |
| `scripts/kimi-ask.sh` | Shell-скрипт с гарантированным сбросом роли (опционально). |
| `Makefile` | `make task MSG="..."` и `make ask MSG="..."` (опционально). |
| `.kimi/skills/auto-agent/SKILL.md` | Skill для Kimi CLI. Активируется через `/skill auto-agent`. |

---

## Ограничение: смена роли внутри сессии

> ⚠️ **Важно:** Роутер (`scripts/kimi-task.sh`) формирует промпт **перед** началом сессии. В рамках одной сессии Kimi CLI LLM может "залипнуть" в предыдущей роли.
>
> **Если в активной сессии нужна другая роль:**
> 1. `make task MSG="..."` — скрипт сформирует полный промпт с правильной ролью (рекомендуется)
> 2. Начни новую сессию Kimi CLI
> 3. Явно укажи роль: `Роль: frontend-dev. Задача: ...`

## Добавление новой роли

1. Создать `.kimi/agents/<new-role>.md` — промпт агента
2. Добавить keywords в `scripts/kimi-task.sh` (функция `detect_role`)
3. Добавить keywords в `.kimi/agents/dispatcher.md` (таблицу роутинга)
4. Добавить keywords в `.kimi/skills/auto-agent/SKILL.md` (таблицу роутинга)
5. Обновить `ROUTER.md` и `SESSION_START.md` (таблицы ролей)
