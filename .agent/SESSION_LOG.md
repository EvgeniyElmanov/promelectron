# SESSION_LOG — Лог изменений по сессиям

> **Append-only.** Агенты только дописывают сверху. Не редактируйте старые записи.

**Формат:**
```
YYYY-MM-DD HH:MM | <role> | <краткое описание>
  Изменено: <файлы>
  Риск/Техдолг: <если есть>
  Блокер: <если появился>
```

---

## Записи (новые сверху)

### 2026-06-07 09:15 | backend-dev | Исправлен баг повторной оплаты заказа
  Изменено:
  - `backend/src/app/services/payment_service.py` — `PaymentService.create_payment()` теперь при существующем неоплаченном платеже создаёт новый платёж в ЮKassa (или mock) и обновляет существующую запись в БД новыми `yookassa_payment_id`, `confirmation_url`, `yookassa_status`, `yookassa_created_at`, `updated_at`. Раньше возвращался старый `confirmation_url` с истёкшим платежом.
  - `backend/tests/test_payments.py` — добавлен патч `YooKassaService.is_configured` (return_value=True) в тесты, использующие мок `create_payment`, чтобы они корректно отрабатывали в окружении без YOOKASSA_SHOP_ID/SECRET_KEY.
  - `backend/tests/test_notifications.py` — аналогичный патч `is_configured` в `test_payment_generates_notification`.
  - `backend/tests/test_orders.py` — аналогичный патч `is_configured` в `test_cancel_paid_order_fails`.
  Риск/Техдолг:
  - Поле `order_id` в `Payment` остаётся `unique=True`, поэтому при повторной оплате обновляется существующая запись (не создаётся новая). Это корректно с точки зрения бизнес-логики (один заказ = один платёж в БД).
  - При переходе от mock к реальной YooKassa логика не изменится — всё равно вызывается `YooKassaService.create_payment` и обновляется запись.
  Блокер: Нет

### 2026-06-06 10:45 | backend-dev | Диагностика YooKassa: debug-логи, webhook raw_body fix, debug endpoint
  Изменено:
  - `backend/src/app/services/yookassa_service.py` — добавлено debug-логирование request/response в create_payment/get_payment; capture теперь берётся из `settings.yookassa_capture_auto` (было hardcoded True)
  - `backend/src/app/services/payment_service.py` — handle_webhook теперь принимает `raw_body` для корректной проверки подписи; добавлены defensive проверки `payment.order is None`; добавлено info-логирование в sync_payment_status_by_order
  - `backend/src/app/api/payments.py` — webhook endpoint теперь считывает `await request.body()` ДО `request.json()` и передаёт raw_body в сервис; добавлен debug endpoint `POST /payments/debug/yookassa/create` (только при test_mode)
  - `backend/src/app/core/config.py` — добавлен `yookassa_capture_auto` (env `YOOKASSA_CAPTURE_AUTO`, default true)
  - `.env.example` — добавлена `YOOKASSA_CAPTURE_AUTO=true`
  - `backend/scripts/diagnose_yookassa.py` — standalone скрипт для диагностики прямого SDK-вызова
  - `backend/tests/test_auth.py` — исправлен `_make_oauth_settings` под новое поле Settings
  - `backend/tests/test_payments.py`, `test_orders.py`, `test_notifications.py` — убраны unused variables (ruff F841)
  Риск/Техдолг:
  - Возможный блокер: YooKassa test shop может отклонять платежи с capture=True для self-employed merchant. Рекомендуется протестировать с `YOOKASSA_CAPTURE_AUTO=false`.
  - Возможный блокер: серверы за пределами РФ могут быть заблокированы YooKassa (известная проблема).
  Блокер: Нет

### 2026-06-06 10:31 | frontend-dev | Исправлен баг в PaymentSuccess.vue: обработка 404 и ошибок fetchOrder
  Изменено:
  - `frontend/src/views/PaymentSuccess.vue` — добавлен `error` ref, `fetchOrder` теперь устанавливает `error.value` при 404 и других ошибках, добавлен блок ошибки в template с `data-testid="payment-error"` и кнопкой "Повторить", title/subtitle при ошибке не показывают "Обработка платежа...", добавлены стили `.payment-result__error`
  Риск/Техдолг: Нет
  Блокер: Нет

### 2026-06-02 21:00 | frontend-dev | YK-005: Frontend редирект на ЮKassa
  Изменено:
  - `frontend/src/views/Checkout.vue` — убраны поля карты, логика: создание платежа → редирект на `confirmation_url`
  - `frontend/src/views/PaymentSuccess.vue` — страница успешной оплаты (order_id из query)
  - `frontend/src/views/PaymentFailed.vue` — страница ошибки оплаты с кнопкой повтора
  - `frontend/src/router/index.js` — добавлены маршруты `/payment/success` и `/payment/failed`
  Риск: Нет
  Блокер: Нет

### 2026-06-02 20:35 | backend-dev | YK-004: Обновление PaymentService + API endpoints
  Изменено:
  - `backend/src/app/services/payment_service.py` — интеграция YooKassaService, handle_webhook, _process_successful_payment, cancel_payment через API
  - `backend/src/app/schemas/payment.py` — добавлены yookassa поля в PaymentOut
  - `backend/src/app/api/payments.py` — удалён mock confirm, добавлен webhook endpoint, обновлён create_payment
  - `backend/tests/test_payments.py` — 7 тестов с моками ЮKassa (все проходят)
  - `backend/tests/test_notifications.py` — обновлён под webhook
  - `backend/tests/test_orders.py` — обновлён под webhook
  Риск: Нет
  Блокер: Нет

### 2026-06-02 20:10 | backend-dev | YK-003: YooKassaService
  Изменено:
  - `backend/src/app/services/yookassa_service.py` — новый сервис: create_payment, get_payment, cancel_payment, create_refund
  - `backend/tests/test_yookassa_service.py` — 6 unit-тестов с моками SDK (все проходят)
  - `backend/tests/test_auth.py` — добавлены yookassa поля в `_make_oauth_settings`
  Риск: SDK синхронный, обёрнут в `asyncio.to_thread`
  Блокер: Нет

### 2026-06-02 19:45 | backend-dev | YK-002: Alembic миграция + исправление BLK-006
  Изменено:
  - `backend/alembic/versions/20260531_222559_guest_order_fields.py` → `b1c2d3e4f5a6_guest_order_fields.py` (исправлено BLK-006)
  - `backend/src/app/models/payment.py` — добавлены поля: yookassa_payment_id, yookassa_status, confirmation_url, payment_method_type, refunded_amount, yookassa_metadata, yookassa_created_at, updated_at
  - `backend/alembic/versions/55b9686a37ab_yookassa_payment_fields.py` — новая миграция (autogenerate)
  - `alembic upgrade head` прошёл успешно (PostgreSQL в Docker)
  Риск: Нет
  Блокер: BLK-006 снят

### 2026-06-02 19:15 | backend-dev | YK-001: ЮKassa SDK + конфигурация
  Изменено:
  - `backend/requirements.txt` — добавлен `yookassa>=3.0.0`
  - `.env.example` — добавлены `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_WEBHOOK_SECRET`, `YOOKASSA_TEST_MODE`
  - `backend/src/app/core/config.py` — `Settings` дополнен полями yookassa_shop_id, yookassa_secret_key, yookassa_webhook_secret, yookassa_test_mode
  Риск: SDK `yookassa` синхронный — потребуется `asyncio.to_thread` в сервисном слое (YK-003)
  Блокер: Нет

### 2026-06-02 18:30 | project-manager | Полный аудит №2 — исправлены все найденные ошибки
  Изменено:
  - `SESSION_START.md` — убрана устаревшая инструкция "Замени <ROLE>"
  - `backend-dev.md` — убраны broken links (.agent/<TASK_ID>/..., review/...), убран git commit
  - `frontend-dev.md` — аналогично backend-dev.md
  - `code-reviewer.md` — убраны ссылки на review/ и .agent/<TASK_ID>/...
  - `tester.md` — убрана ссылка на .agent/<TASK_ID>/review/test-findings.md
  - `PROJECT_CONTEXT.md` — убрано дублирование дат (теперь только в YAML frontmatter)
  - `Makefile` — добавлен `task-compact` target
  - `backend-dev.md`, `frontend-dev.md` — убран `Bash(git commit *)` из allowedTools
  Риск: Нет
  Блокер: Нет

### 2026-06-02 18:15 | project-manager | SESSION_START.md упрощён до 5 строк
  Изменено:
  - `SESSION_START.md` — Вариант А теперь компактный (5 строк вместо 40)
  - Добавлен Вариант Б — «Если сессия уже активна — просто пиши Задача: ...»
  - Убран длинный универсальный промпт с ручным определением роли
  Риск: Нет
  Блокер: Нет

### 2026-06-02 18:00 | project-manager | Внедрены улучшения: git hook, YAML frontmatter, AI self-check
  Изменено:
  - `.git/hooks/pre-push` — предупреждение перед push если линтер падает
  - `PROJECT_CONTEXT.md` — добавлен YAML frontmatter (machine-readable метрики)
  - `.kimi/rules/ai-self-check.md` — правила для AI-ассистента (проверка фактов, diff, обновление логов)
  - `.kimi/AGENTS.md` — добавлен ai-self-check в список rules
  Риск: pre-push hook может быть медленным на больших изменениях
  Блокер: Нет

### 2026-06-02 17:30 | project-manager | Полный аудит системы агентов — исправлены конфликты
  Изменено:
  - Удалены: `.agent/AGENTS.md` (дублировал корневой), `.agent/CONTEXT.md` (устарел)
  - Удалён: `.kimi/agents/qa.md` (дублировал tester.md)
  - Исправлен: `.kimi/rules/agent-first.md` — убрана ложная инструкция "never edit files" из Claude Code
  - Исправлен: `.kimi/agents/integration-dev.md` — `client/` → `frontend/`
  - Исправлены skills в backend-dev, frontend-dev, devops — убраны несуществующие skills
  - Обновлён: `SESSION_START.md` — добавлены ссылки на новые rules
  - Обновлён: `.kimi/AGENTS.md` — добавлены новые rules и skills
  - Обновлён: `AGENTS.md` (корневой) — добавлен раздел о системе агентов
  Риск: Удаление файлов могло сломать ссылки — проверить нужно
  Блокер: Нет

### 2026-06-02 16:00 | project-manager | Созданы guard-правила для агентов
  Изменено:
  - `.kimi/rules/pre-edit-checklist.md` — чеклист перед правкой кода (тесты, миграции, env, линтер)
  - `.kimi/rules/golden-path.md` — 5 критичных сценариев, которые нельзя ломать
  - `.kimi/rules/dependency-map.md` — таблица связей Model→Schema→Service→Route→Test
  Риск: Агенты могут игнорировать чеклист — нужно контролировать
  Блокер: Нет

### 2026-06-02 15:30 | project-manager | Изучена документация ЮKassa, составлен план интеграции
  Изменено:
  - `.agent/tasks/TASK-001-yookassa-integration.md` — детальный план (Phase 1-4)
  - `.agent/BACKLOG.md` — детализация задачи #1 на подзадачи 1a-1h
  - `PROJECT_CONTEXT.md` — обновлён API Inventory (endpoints payments)
  Документация: `/home/evgeniy/Загрузки/yookassa-docs/`
  Риск: SDK `yookassa` может быть синхронным — нужно проверить и обернуть в to_thread
  Блокер: BLK-006 (Alembic) мешает миграции Payment

### 2026-06-02 14:30 | project-manager | Создана система контекста для агентов
  Изменено:
  - `PROJECT_CONTEXT.md` — единый источник контекста
  - `.kimi/rules/task-template.md` — шаблон задачи
  - `.kimi/agents/project-manager.md` — ритм работы, формат задач
  - `.kimi/AGENTS.md` — обязательные файлы для чтения
  - `AGENTS.md` (корневой) — упоминание PROJECT_CONTEXT.md
  - `SESSION_START.md` — шаблон входа в сессию
  - `.agent/SESSION_LOG.md` — этот файл
  - `Makefile` — добавлены `agent-context`, `agent-status`
  Риск/Техдолг: Нужно привыкнуть дописывать SESSION_LOG после каждой сессии
  Блокер: Нет

---

### 2026-06-02 16:55 | project-manager | Показан текущий план проекта по запросу пользователя
  Изменено:
  - `.agent/SESSION_LOG.md` — эта запись
  Риск/Техдолг: Нет
  Блокер: Нет

---

*Старые записи будут ниже, когда появятся.*

## 2026-06-02 17:59

**Роль:** project-manager (router fix)

**Что сделано:**
- Исправлен роутер scripts/kimi-task.sh — 28/28 тестов проходят
- Исправлен lowercase для кириллицы: tr → python3 (tr не обрабатывает UTF-8 upper/lower)
- Исправлено склонение 'страница' → 'страниц[аеиоуыюя]?' (ловит страницу/страницы/странице)
- Исправлено склонение 'корзина' → 'корзин[аеиоуыюя]?' для UI-задач
- Добавлен hybrid паттерн для API integration задач (frontend-dev)
- Исправлено 'бэк' → 'бэк\b' чтобы не ловить 'бэклог' как backend
- Исправлено 'код' → 'код[аеиоуыюя]?' для review задач (качество кода)
- Убран trailing \b для e2e regex (проблемы с опциональными окончаниями)
- Добавлены mobile/мобильн паттерны в e2e keywords

**Файлы:** scripts/kimi-task.sh, scripts/test-router.sh

**Риски:** Нет

---

## 2026-06-02 18:04

**Роль:** project-manager (full system check)

**Что сделано:**
- Полный аудит агентской системы (audit-agents.sh) — все проверки проходят
- Проверка роутера (test-router.sh) — 28/28 тестов проходят
- Исправлен review/SKILL.md: убрана битая ссылка review/quick-findings.md → .agent/REVIEW_FINDINGS.md
- Исправлен PROJECT_CONTEXT.md: cd backend && make dev-backend → make dev-backend (target в корне)
- Исправлен Makefile: agent-context target был обрезан (только заголовок), дописан полный вывод контекста
- Проверены все агенты (.kimi/agents/*.md) — битых ссылок нет, git commit убран
- Проверены все rules (.kimi/rules/*.md) — консистентны
- Проверены все skills (.kimi/skills/*) — битых ссылок нет (кроме исправленной)

**Файлы изменены:** Makefile, PROJECT_CONTEXT.md, .kimi/skills/review/SKILL.md

**Риски:** Нет

---

## 2026-06-02 18:14

**Роль:** project-manager (role-switching clarification)

**Что сделано:**
- Проверена логика смены роли в рамках одной сессии Kimi CLI
- SESSION_START.md: добавлено предупреждение про 'инерцию роли' LLM в Вариант Б
- auto-agent/SKILL.md: добавлен раздел 'Ограничение: смена роли в рамках одной сессии'
- ROUTER.md: добавлен раздел про ограничение смены роли внутри сессии

**Файлы изменены:** SESSION_START.md, .kimi/skills/auto-agent/SKILL.md, ROUTER.md

**Риски:** Нет

---

## 2026-06-02 18:26

**Роль:** project-manager (dispatcher agent + all 3 variants)

**Что сделано:**
- Создан .kimi/agents/dispatcher.md — универсальный диспетчер, который определяет роль при КАЖДОМ запросе
- SESSION_START.md: добавлен Вариант Г (Диспетчер) как рекомендуемый для автопереключения ролей
- SESSION_START.md: Вариант А усилен предупреждением про инерцию роли
- ROUTER.md: добавлен dispatcher в таблицу ролей и архитектуру
- AGENTS.md: добавлен dispatcher в таблицу агентов
- auto-agent/SKILL.md: обновлен раздел ограничений — диспетчер как решение #1
- audit-agents.sh: проходит (все проверки OK)
- test-router.sh: 28/28 тестов проходят

**Файлы изменены:** .kimi/agents/dispatcher.md (новый), SESSION_START.md, ROUTER.md, AGENTS.md, .kimi/skills/auto-agent/SKILL.md

**Риски:** Нет

---

## 2026-06-02 18:34

**Роль:** project-manager (kimi-ask.sh — гарантированный сброс роли)

**Что сделано:**
- Создан scripts/kimi-ask.sh — скрипт, который формирует полный промпт с диспетчером + инструкции агента + контекст
- Отличие от kimi-task.sh: вставляет содержимое .kimi/agents/<ROLE>.md прямо в промпт (не требует чтения файлов LLM)
- Добавлен Makefile target: make ask MSG="..."
- Обновлён audit-agents.sh: проверяет make ask
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** scripts/kimi-ask.sh (новый), Makefile, scripts/audit-agents.sh

**Риски:** Нет

---

## 2026-06-02 18:46

**Роль:** project-manager (полный переход на Kimi CLI без bash)

**Что сделано:**
- Создан .agent/DISPATCHER_PROMPT.md — главный файл для автопереключения ролей внутри Kimi CLI
- SESSION_START.md полностью переписан: убраны все bash-команды, только текстовые инструкции для чата
- AGENTS.md обновлён: быстрый старт через DISPATCHER_PROMPT.md, убраны bash-команды из основного workflow
- ROUTER.md обновлён: Способ 1 — диспетчер (Kimi CLI), Способ 2 — фиксированная роль, Способ 3 — bash (опционально)
- audit-agents.sh обновлён: проверяет DISPATCHER_PROMPT.md и диспетчер в SESSION_START.md
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** .agent/DISPATCHER_PROMPT.md (новый), SESSION_START.md, AGENTS.md, ROUTER.md, scripts/audit-agents.sh

**Риски:** Нет

---

## 2026-06-02 18:56

**Роль:** project-manager (full audit + bug fixes)

**Что сделано:**
- Удалён .kimi/agents/tester.md — полностью дублировал e2e-tester.md
- Обновлён e2e-tester.md: добавлен YAML frontmatter, убран browser_take_screenshot (Claude-specific), заменён на page.screenshot()
- Обновлён integration-dev.md: добавлен YAML frontmatter, уточнена зона ответственности (только dev-окружение)
- Обновлён security-reviewer.md: добавлен YAML frontmatter
- Исправлен code-reviewer.md: spec.md → task-template.md, убрана ссылка на несуществующий client.py
- Обновлён CLAUDE.md: добавлен dispatcher, убран tester, добавлены security-reviewer и code-reviewer
- Исправлена таблица агентов в AGENTS.md: добавлен security-reviewer, удалён tester, исправлена разорванная таблица
- Обновлён ROUTER.md: добавлены cart (API/UI) и checkout (UI) keywords
- Исправлен .agent/tasks/README.md: review.md → REVIEW_FINDINGS.md
- Все агенты теперь имеют YAML frontmatter (консистентность)
- audit-agents.sh: проходит (все проверки OK)
- test-router.sh: 28/28 тестов проходят

**Файлы изменены:** .kimi/agents/e2e-tester.md, integration-dev.md, security-reviewer.md, code-reviewer.md, CLAUDE.md, AGENTS.md, ROUTER.md, .agent/tasks/README.md

**Риски:** Нет

---

## 2026-06-04 15:52

**Роль:** project-manager (added mixed-role mode)

**Что сделано:**
- SESSION_START.md: добавлен раздел 'Вариант: Сквозная фича' для задач, требующих нескольких ролей (например, YooKassa E2E → CI/CD → backend → Helm)
- .agent/DISPATCHER_PROMPT.md: добавлено исключение для сквозных задач — диспетчер работает гибко, не сбрасывая контекст между блоками
- .kimi/agents/dispatcher.md: добавлено то же исключение для сквозных задач
- audit-agents.sh: проходит (все проверки OK)

**Файлы изменены:** SESSION_START.md, .agent/DISPATCHER_PROMPT.md, .kimi/agents/dispatcher.md

**Риски:** Нет

---
