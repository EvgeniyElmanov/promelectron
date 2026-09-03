# 🤖 AI Agent System — Promelectron

Этот проект использует **Kimi Code CLI** с проектными инструкциями в `.kimi-code/AGENTS.md`, workflow-навыками в `.kimi-code/skills/` и консолидированным реестром навыков/правил в `.kimi-code/BUNDLE.md`.

## Документация

- **`.kimi-code/AGENTS.md`** — проектные инварианты, обзор workflow, разрешения и правила пост-работы.
- **`.kimi-code/BUNDLE.md`** — консолидированный реестр ролевых и workflow-навыков, а также общих правил.
- **`.kimi-code/HOWTO.md`** — практическое руководство: маршрутизация задач, workflow и решение проблем.
- **`.kimi-code/LESSONS_LEARNED.md`** — уроки по E2E CI.
- **`PROJECT_CONTEXT.md`** — единый источник истины по стеку, фичам, блокерам и API-инвентарю.
- **`docs/guides/session-start.md`** — шаблоны входа в сессию и ежедневный workflow.
- **`docs/guides/agent-routing.md`** — документация по маршрутизации агентов.
- **`docs/README.md`** — навигация по всей документации проекта.

## Пульт запуска

- **`ai-launcher/BOARD.md`** — что можно брать прямо сейчас, какие замки заняты, что ждёт условия.
- **`ai-launcher/CONVENTIONS.md`** — форма пульта, замки, порядок сверки. Общий документ для
  Claude Code и Kimi Code.
- **`ai-launcher/README.md`** — как настроить лончер на своей машине (`Makefile.override.mk`).

Кнопка запуска у всех одна — `make ai PROMPT=…`; чем она запускается (claude или kimi), задаётся
машинно-локально. Команды: `/board`, `/sessions` (Claude) · `/skill:board`, `/skill:sessions` (Kimi).
