

# Блокеры Promelectron

**Версия:** 1.1
**Дата:** 2026-06-02
**Правило:** Project-manager проверяет каждый день в 10:00 MSK. Блокер >2 дней — эскалация пользователю.

---

## Активные блокеры

| ID | Дата | Блокер | Severity | Затронуто | Кто решает | Статус | План B | Дедлайн |
|----|------|--------|----------|-----------|------------|--------|--------|---------|
| BLK-001 | 2026-05-30 | `.github/` защищена — CI/CD правки требуют ручного доступа | P1 | Helm, deploy.yml, worker templates | devops | **🔴 эскалирован** | Править вручную через админа | 2026-06-02 |
| BLK-002 | 2026-05-30 | `worker.enabled=false` в Helm + сломанная команда `python -m app.workers.queue_worker` — Celery не работает в K8s | P0 | 1C sync, email, notifications, background tasks | devops | **🟡 частично решён** | Worker задеплоен вручную через `kubectl apply` (concurrency=2, memory 512Mi). Helm release `promelectron-test` отсутствует — нужно восстановить CI/CD для полного фикса. | 2026-06-12 |
| BLK-004 | 2026-05-30 | `API_BASE_URL` в K8s test окружении не настроен | P1 | E2E тесты, фронтенд | devops | ждёт конфиг | Hardcode в nginx.conf временно | 2026-06-05 |
| BLK-006 | 2026-06-02 | Malformed revision ID в Alembic миграции `20260531_222559_guest_order_fields.py` (`revision = 'b1c2d3e4f5a6'`) — некорректная миграционная история | P1 | Миграции БД, `alembic upgrade head` | backend-dev | **🟡 в работе** | Пересоздать миграцию с корректным revision ID | 2026-06-04 |
| BLK-007 | 2026-06-06 | YooKassa test shop отклоняет платежи со страницы 'Не сработало'. API create_payment работает (curl + backend debug endpoint возвращают confirmation_url), но оплата на странице YooKassa не проходит. Возможные причины: capture=True для self-employed merchant, IP/регион блокировка, временный сбой YooKassa, неверная тестовая карта. | P1 | Интеграция платежей, E2E тест checkout | backend-dev | **✅ решён** | Проверить с YOOKASSA_CAPTURE_AUTO=false; проверить тестовую карту 5555...4444; проверить регион сервера | 2026-06-07 |
| BLK-009 | 2026-06-22 | CDEK widget-service `calculate` возвращает 502 Bad Gateway на test-окружении при `action=calculate` с `to_location.address` без `code`. `action=offices` работает. Блокирует UI-выбор доставки при гостевом чекауте. | P1 | Гостевой чекаут, CDEK доставка | backend-dev / devops | **🔴 в работе** | Создание заказа через API с фиктивными CDEK-данными; починить прокси/геокодирование | 2026-06-23 |
| BLK-010 | 2026-06-22 | YooKassa webhook `payment.succeeded` не приходит на `/api/v1/payments/yookassa/webhook/` в test-окружении. Заказы остаются в `pending` после успешной оплаты до ручной синхронизации или имитации webhook. | P1 | YooKassa интеграция, статусы заказов | devops / project-manager | **🔴 в работе** | Ручная синхронизация через API; настроить webhook URL в личном кабинете YooKassa | 2026-06-23 |
| BLK-011 | 2026-06-22 | Отсутствовали frontend-страницы сброса пароля (`/forgot-password`, `/reset-password`). | P2 | Гостевой чекаут, UX | frontend-dev | **✅ решён** | — | 2026-06-22 |
---

## Эскалированные (>2 дней)

| ID | Дата открытия | Дней открыт | Действие |
|----|---------------|-------------|----------|
| BLK-001 | 2026-05-30 | 3 | Требуется ручное разрешение пользователя для изменения `.github/workflows/` и push в main |
| BLK-002 | 2026-05-30 | 3 | **P0**: Celery worker в K8s полностью неработоспособен. Нужен доступ к `.github/` для фикса CI/CD + правка Helm templates. Требуется решение: править вручную или дать доступ агенту. |

---

## Решённые блокеры

| ID | Дата | Блокер | Severity | Решение | Затраченное время |
|----|------|--------|----------|---------|------------------|
| BLK-005 | 2026-06-26 | Нет реальных SMTP кредов — email в fallback-режиме | P1 | Креды Yandex SMTP (app password) получены; backend-реализация Phase 1+2 готова в задаче #43/#19. Frontend + Helm values — в работе. | — |
| BLK-007 | 2026-06-06 | YooKassa test shop отклонял платежи со страницы 'Не сработало' | P1 | Использовать тестовую карту 5555...4477 + проходить 3DS sandbox; платёж проходит, capture работает. Добавлен `completeYooKassaPaymentIfNeeded` в E2E helpers. | 3 часа |
| BLK-R001 | 2026-05-28 | PostgreSQL enum cleanup — тесты падали | P1 | Добавить `DROP TYPE IF EXISTS roleenum CASCADE` в `conftest.py` + `NullPool` | 4 часа |
| BLK-R002 | 2026-05-28 | E2E checkout timeout — 10 секунд не хватало | P1 | `waitForURL` → `waitForResponse` + `toHaveURL` с 30s | 2 часа |
| BLK-R003 | 2026-05-28 | Rate limiting в CI — `ENVIRONMENT=production` ломал тесты | P1 | Поднять limits для `/login` и `/orders/create` до 50/min | 1 час |
| BLK-R004 | 2026-05-28 | FK violation при seed reset — удаление users ломало suppliers | P1 | Убрать удаление users из `reset_test_state`, оставить только orders/carts | 3 часа |
| BLK-R005 | 2026-05-28 | Email timeout в тестах — SMTP блокировал | P1 | `asyncio.wait_for(..., 5s)` + try/except в `EmailService` | 2 часа |
| BLK-R006 | 2026-05-30 | `frontend/Dockerfile` с `USER nginx` — rollout timed out в CI/CD | P0 | Откат до `3b51d2e`, rebuild через `.dockerignore` | 2 часа |
| BLK-R007 | 2026-05-31 | E2E auth.spec.js ожидал редиректа `/cart` → `/login` после гостевой корзины | P1 | Обновить тест: гость видит корзину, checkout ведёт на login | 1 час |
| BLK-008 | 2026-06-22 | `FRONTEND_URL=http://localhost:5173` в `backend/docker-compose.yml` ломает E2E mock-редирект внутри Docker | P1 | Изменить `FRONTEND_URL` и `API_BASE_URL` на `http://frontend:5173` / `http://api:8000` для api/worker/beat в `backend/docker-compose.yml` | 30 мин |

---

## Формат добавления нового блокера

```markdown
| BLK-NNN | YYYY-MM-DD | Описание | P0/P1/P2 | Задачи #X, #Y | КТО | статус | План B | YYYY-MM-DD |
```

## Предотвращённые

| Дата | Потенциальный блокер | Почему не случился |
|------|----------------------|--------------------|
| 2026-05-30 | Повторный деплой `USER nginx` без temp dirs | Решено отложить non-root containers до Sprint 2, когда будут readiness probes |

---

**Severity:**
- **P0** — полная остановка разработки или деплоя
- **P1** — замедление, обходные пути есть
- **P2** — неудобство, можно ждать
