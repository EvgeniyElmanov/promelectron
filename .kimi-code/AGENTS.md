# 🤖 AI Agent System — Promelectron

> Проектные инструкции для Kimi Code CLI.  
> Загружаются автоматически из `.kimi-code/AGENTS.md` для каждой сессии в этом проекте.

> **Примечание:** инструкции, специфичные для ролей, находятся в flat Kimi skills в `.kimi-code/skills/<role>/`.  
> Общие конвенции живут в `.kimi-code/rules/` (reference markdown, не skills).  
> Этот файл — мастер-индекс и содержит только проектные инварианты.

---

## Реестр навыков и правил

Консолидированный реестр ролевых навыков, workflow-навыков и общих правил см. в `.kimi-code/BUNDLE.md`.

---

## 🚨 ЗОЛОТОЕ ПРАВИЛО: язык ответов

Когда пользователь общается на русском:

- **Финальные ответы пользователю, отчёты и артефакты пиши на русском.**
- **Стремись рассуждать на русском.** Но учти: модель Kimi K3 работает с
  принудительным thinking mode (отключить нельзя, глубина задаётся `reasoning_effort`),
  и язык внутреннего рассуждения промптом надёжно не
  управляется — не считай сбой языка *thinking* ошибкой выполнения, критичен язык
  ответов и артефактов.
- **Делегируя субагентам**, добавляй языковую преамбулу из единого источника (см. ниже)
  в начало и конец их промпта.
- Код, команды, идентификаторы, пути к файлам и технические термины оставляй в оригинале.

Единый источник истины о языке (формулировка правила и точная преамбула для субагентов):
[Rule: Agent Commons](./rules/agent-commons.md) > Language Rule / Языковое правило.

## Границы субагентов

- Субагенты, запущенные через инструмент `Agent`, работают в изолированном контексте и **не могут запускать вложенные субагентов**.
- Только основной агент (или top-level вызов skill) может вызывать `Agent` или `AgentSwarm`.
- Для параллельной работы (например, одновременно review backend + frontend) **основной агент** использует `AgentSwarm`; один субагент не должен пытаться порождать пиров.

---

## Быстрый старт

```bash
# Реализовать новую фичу (полный цикл)
/skill:implement "Add promo codes to cart"

# Написать спецификацию без кодирования
/skill:spec "Add promo codes to cart"

# Исправить баг или упавшие тесты
/skill:fix "Race condition in cart add"

# Ревью текущих изменений
/skill:review

# Перезапустить QA для существующей задачи
/skill:qa-gate add-promo-codes-to-cart-0624

# Открыть PR для текущей ветки
/skill:ship

# Деплой в test или prod
/skill:deploy test

# Синхронизировать контекст проекта
/skill:context-sync

# Поддержка планов
/skill:plan-maintainer analyze

# Анализ повторяющихся failure patterns пайплайна (continuous improvement)
/skill:plan-maintainer improve

# Визуальный статус пайплайна задачи (Mermaid, read-only)
/skill:flow-implement add-promo-codes-to-cart-0624
/skill:flow-fix fix-yookassa-cancel-reason-84
/skill:flow-review add-promo-codes-to-cart-0624
```

---

## Где что лежит

| Путь | Назначение |
|------|------------|
| `.kimi-code/skills/` | Flat Kimi skills для ролей и workflow |
| `.kimi-code/AGENTS.md` | Этот файл — только проектные инварианты |
| `.kimi-code/rules/` | Общие конвенции и reference-документы |
| `.kimi-code/mcp.json` | Конфигурация MCP-серверов |
| `.kimi-code/config.example.toml` | Пример пользовательской конфигурации |
| `scripts/implement-pipeline.py` | Хелпер для task ID, git worktrees, review loops |
| `scripts/agent_state.py` | Typed state + детекция фазы пайплайна + trace.jsonl с correlation ID (observability) |
| `scripts/mcp_figma.py` | MCP-сервер: Figma design tokens / styles / components |
| `scripts/mcp_atlassian.py` | MCP-сервер: Jira issues + Confluence pages |
| `docs/MCP_INTEGRATION.md` | Настройка токенов и использование MCP-серверов figma/atlassian |
| `.agent/runs/<task-id>/` | Gitignored coordination plane для задачи (`task.md`, `spec.md`, `review/findings.md`, `review/test-findings.md`) |
| `.worktrees/<task-id>/` | Изолированный git worktree для feature-ветки |
| `ai-launcher/BOARD.md` | **Пульт запуска** — витрина открытых GitHub Issues: что можно брать, какие замки заняты, что ждёт условия |
| `ai-launcher/CONVENTIONS.md` | Форма пульта, замки, порядок сверки — **общий документ с Claude Code**, там же таблица замков |
| `ai-launcher/prompts/` | Промпты запуска пунктов (`make ai PROMPT=…`) |
| `Makefile.override.mk` | Машинно-локальные цели (gitignored). Задаёт `AI_CMD` — чем запускается кнопка борда: у одного kimi, у другого claude. Образец — `ai-launcher/README.md` |

---

## Обзор workflow

```
Пользователь: /implement "Add promo codes to cart"
        │
        ▼
   Создать .agent/runs/<task-id>/
        │
        ▼
   git worktree add .worktrees/<task-id> -b feature/<task-id>
        │
        ▼
   Субагент architect (plan mode) → spec.md → пользователь одобряет
        │
        ▼
   Субагент(ы) developer в worktree (backend-dev / frontend-dev / devops)
        │
        ▼
   Субагент(ы) code reviewer (максимум 3 итерации)
        │
        ▼
   Субагент QA (pytest + vitest + Playwright, проверяет Acceptance Criteria)
        │
        ▼
   Открыть PR через gh pr create → оставить комментарии [H-xxx]
        │
        ▼
   Отчёт пользователю → merge только с явным одобрением
```

### Флаги

- `--quick` — пропустить фазу architect/spec.
- `--backend-only` — только backend-разработка.
- `--frontend-only` — только frontend-разработка.
- `--serial` — запускать backend, затем frontend последовательно (по умолчанию параллельно).
- `--qa` — запустить dedicated QA gate перед открытием PR.

---

## Жёсткие правила

- **NEVER** продолжать предыдущую роль для новой задачи.
- **NEVER** смешивать роли в одной задаче.
- **NEVER** создавать DB model без миграции.
- **NEVER** писать endpoint без тестов.
- **NEVER** коммитить без явного одобрения пользователя.
- **ALWAYS** использовать trailing slash в НОВЫХ FastAPI endpoints (`/items/`, not `/items`).
- **NEVER** менять существующие endpoints без trailing slash без отдельной задачи — redirect-риски, фронтенд зависит от текущих путей (например, `/cart/merge`, `/admin/orders`, `/supplier/profile`).
- **ALWAYS** запускать тесты перед отчётом о завершении.
- **ALWAYS** привязывать GitHub Issue перед началом разработки в `/skill:implement`.
- **ALWAYS** обновлять статус GitHub Project board на границах фаз: spec approved → In progress, PR open → In review, merged → Done.
- **NEVER** создавать дублирующие GitHub Issues для одного и того же `task-id`; переиспользуй существующий `github_issue` из `task.md`.

---

## Обязательный контекст (читать перед каждой задачей)

1. `PROJECT_CONTEXT.md` — стек, статус фич, блокеры, инвентарь API
2. `.agent/BACKLOG.md` — текущий спринт
3. `.agent/BLOCKERS.md` — активные блокеры
4. `.agent/SESSION_LOG.md` — недавние сессии (только tail ~200 строк)
5. `ai-launcher/BOARD.md` — пульт запуска: что свободно, какие замки заняты, что ждёт условия
6. Соответствующий ролевой skill в `.kimi-code/skills/<role>/SKILL.md`
7. [Rule: Agent Commons](./rules/agent-commons.md) — язык, retry policy, размер контекста, ограничения API
8. [Rule: Pre-edit Checklist](./rules/pre-edit-checklist.md) (перед изменением кода)
9. [Rule: Business Rules](./rules/business.md) — инварианты интернет-магазина (цены, stock, заказы, платежи, доставка, возвраты)

---

## Обновления после работы

После завершения любой задачи:

1. Обновить `.agent/SESSION_LOG.md`.
2. Обновить `.agent/BACKLOG.md`, если задача из спринта.
3. Обновить `.agent/BLOCKERS.md`, если появился новый блокер.
4. Обновить `PROJECT_CONTEXT.md`, если изменилась архитектура.
5. Обновить `ai-launcher/BOARD.md`: снять закрытый пункт, освободить замок, пересчитать блок
   «Замки». Борд, который не обновили, начинает врать уже через сессию — и коллега на другом
   агенте возьмёт занятое.

---

## Разрешения

**Разрешено:**
- `make *`, `pytest *`, `alembic *`, `ruff *`
- `git status`, `git diff`, `git log`, `git worktree *`, `git commit *` (только feature-ветки)
- `npm *`, `npx *`
- `docker *`, `kubectl *`, `helm *`
- `gh workflow run *`, `gh run *`

**Запрещено:**
- `rm -rf *`
- `git push --force *`
- `git reset --hard *`
- `DROP *`, `truncate *`

Safety hooks (PreToolUse, см. `.kimi-code/config.example.toml`, скрипты в `scripts/hooks/`): `block-dangerous-bash.py` — опасные команды; `block-main-git-mutations.py` — git commit/push/merge на ветке `main`; `single-test-run.py` — параллельный `make test-backend`/`test-frontend` при занятом flock.

---

## Перед push

Запустить `make pre-push` (lint + unit tests + E2E) перед push feature-ветки.

Правила push:
- Push веток `feature/*` и `bugfix/*` в origin авто-одобряется через правила разрешений в `~/.kimi-code/config.toml`.
- Push в `main` требует явного одобрения пользователя (permission rule использует `decision = "ask"`).

CI запускает E2E suite в окружении `promelectron-test` после деплоя.

---

## См. также

- [Rule: Agent Commons](./rules/agent-commons.md) — языковое правило, retry policy, обработка размера контекста
- [Rule: Planning & Definition of Done](./rules/planning.md) — формат задачи, приоритизация, Definition of Done
- [Rule: Business Rules](./rules/business.md) — инварианты интернет-магазина
- [Rule: Known Pitfalls](./rules/known-pitfalls.md) — реальные проблемы, которые уже случались
