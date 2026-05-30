# Блокеры Promelectron

**Версия:** 1.0
**Дата:** 2026-05-30
**Правило:** Project-manager проверяет каждый день в 10:00 MSK. Блокер >2 дней — эскалация пользователю.

---

## Активные блокеры

| ID | Дата | Блокер | Severity | Затронуто | Кто решает | Статус | План B | Дедлайн |
|----|------|--------|----------|-----------|------------|--------|--------|---------|
| BLK-001 | 2026-05-30 | `.github/` защищена — CI/CD правки требуют ручного доступа | P1 | Helm, deploy.yml | devops | ждёт доступа | Править вручную через админа | 2026-06-02 |
| BLK-002 | 2026-05-30 | `worker.enabled=false` в Helm — Celery не работает в K8s | P0 | 1C sync, email, notifications | devops | в работе | Временно cron + manual trigger | 2026-06-02 |
| BLK-003 | 2026-05-30 | `frontend/Dockerfile` с `USER nginx` — rollout timed out в CI/CD | P0 | Frontend деплой | devops | расследование | Временно убрать `USER nginx`, оставить root | 2026-06-02 |
| BLK-004 | 2026-05-30 | `API_BASE_URL` в K8s test окружении не настроен | P1 | E2E тесты, фронтенд | devops | ждёт конфиг | Hardcode в nginx.conf временно | 2026-06-05 |
| BLK-005 | 2026-05-30 | Нет реальных SMTP кредов — email в fallback-режиме | P1 | Email notifications | project-manager | ждёт данных от пользователя | Graceful skip (уже реализовано) | 2026-06-10 |

---

## Решённые блокеры

| ID | Дата | Блокер | Severity | Решение | Затраченное время |
|----|------|--------|----------|---------|------------------|
| BLK-R001 | 2026-05-28 | PostgreSQL enum cleanup — тесты падали | P1 | Добавить `DROP TYPE IF EXISTS roleenum CASCADE` в `conftest.py` + `NullPool` | 4 часа |
| BLK-R002 | 2026-05-28 | E2E checkout timeout — 10 секунд не хватало | P1 | `waitForURL` → `waitForResponse` + `toHaveURL` с 30s | 2 часа |
| BLK-R003 | 2026-05-28 | Rate limiting в CI — `ENVIRONMENT=production` ломал тесты | P1 | Поднять limits для `/login` и `/orders/create` до 50/min | 1 час |
| BLK-R004 | 2026-05-28 | FK violation при seed reset — удаление users ломало suppliers | P1 | Убрать удаление users из `reset_test_state`, оставить только orders/carts | 3 часа |
| BLK-R005 | 2026-05-28 | Email timeout в тестах — SMTP блокировал | P1 | `asyncio.wait_for(..., 5s)` + try/except в `EmailService` | 2 часа |

---

## Формат добавления нового блокера

```markdown
| BLK-NNN | YYYY-MM-DD | Описание | P0/P1/P2 | Задачи #X, #Y | КТО | статус | План B | YYYY-MM-DD |
```

**Severity:**
- **P0** — полная остановка разработки или деплоя
- **P1** — замедление, обходные пути есть
- **P2** — неудобство, можно ждать
