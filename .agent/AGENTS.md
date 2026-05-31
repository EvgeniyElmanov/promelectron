# Реестр агентов Promelectron

**Версия:** 1.0
**Дата:** 2026-05-30

---

## Агенты и зоны ответственности

| Агент | Зона | Разрешено | Запрещено | Ключевое правило |
|-------|------|-----------|-----------|------------------|
| **backend-dev** | `backend/src/app/`, `backend/tests/`, `backend/alembic/` | API, models, services, migrations, Celery tasks, tests | `frontend/`, `.infra/helm/`, `.github/`, `.agent/` (чтение разрешено) | Не выходить за зону без согласования с project-manager |
| **frontend-dev** | `frontend/src/`, `frontend/e2e/` (чтение) | Vue views, components, composables, router, API integration | `backend/`, `.infra/helm/`, `.github/`, `.agent/` (чтение разрешено) | Проверять mobile-адаптивность на 320px–1440px |
| **devops** | `Dockerfile`, `.infra/helm/`, CI/CD configs, `docker-compose.yml` | Инфраструктура, деплой, мониторинг, безопасность контейнеров | Бизнес-логика, UI, `.agent/` (чтение разрешено) | Не коммитить секреты — только references и шаблоны |
| **e2e-tester** | `frontend/e2e/` | Playwright тесты, тест-планы, баг-репорты | Код продукта (`src/`), `.agent/` (чтение разрешено) | Тесты проходят перед merge в main — zero exceptions |
| **project-manager** | `.agent/`, `docs/`, планирование, координация | Планы, задачи, метрики, roadmap, приоритизация | Код продукта (чтение разрешено) | Пишет планы — не правит `main.py` |

---

## Общие правила для всех агентов

### Agent-first rule
Все изменения кода проходят через специализированных агентов. Прямое редактирование файлов разрешено только для:
- Однострочных исправлений (опечатки, очевидные баги)
- Чтения файлов для понимания контекста

### Единый источник правды
- **План:** `.agent/PLANNING_HANDOFF.md` (долгосрочная дорожная карта) + `.agent/BACKLOG.md` (текущие задачи)
- **Статус:** `.agent/CONTEXT.md`
- **Блокеры:** `.agent/BLOCKERS.md`
- **Архитектурные решения:** `.agent/DECISIONS.md`
- **Метрики:** `.agent/METRICS.md`

Агенты НЕ читают `PLAN.md` (устарел, заархивирован). Все вопросы по плану — к `project-manager`.

### Запреты
- **Не переписывать с нуля** без обоснования и approve project-manager
- **Не ломать CI/CD** — перед коммитом проверять, что pipeline зелёный
- **Не коммитить в `.github/` и `.infra/helm/`** без devops-агента
- **Не блокировать гостевой функционал** без бизнес-обоснования
- **Не коммитить секреты** — env vars, пароли, токены только через K8s Secrets

### Запрос помощи другому агенту
1. Создать задачу в `.agent/BACKLOG.md`
2. Указать: кто запрашивает, что нужно, зачем, критичность, желаемый срок
3. Project-manager приоритизирует и назначает исполнителя

### Emergency protocol
- **Обнаружен секрет в коде** → Сразу project-manager + devops, ротация секрета
- **CI/CD down** → devops, уведомить project-manager
- **Production incident** → devops + backend-dev, project-manager эскалирует пользователю

---

## Расписание проверок

| Что | Кто | Когда |
|-----|-----|-------|
| Статус спринта | project-manager | Ежедневно 10:00 MSK |
| Блокеры >2 дней | project-manager | Ежедневно 10:00 MSK |
| Метрики | project-manager | По пятницам |
| Security scan | devops | Еженедельно |
| Dependency audit | backend-dev | Ежемесячно |
