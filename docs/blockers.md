

# Блокеры Promelectron

**Версия:** 1.4
**Дата:** 2026-08-28
**Правило:** Project-manager проверяет каждый день в 10:00 MSK. Блокер >2 дней — эскалация пользователю.

---

## Активные блокеры

| ID | Дата | Блокер | Severity | Затронуто | Кто решает | Статус | План B | Дедлайн |
|----|------|--------|----------|-----------|------------|--------|--------|---------|
| BLK-009 | 2026-06-22 | CDEK widget-service `calculate` возвращает 502 Bad Gateway на test-окружении при `action=calculate` с `to_location.address` без `code`. `action=offices` работает. Блокирует UI-выбор доставки при гостевом чекауте. | P1 | Гостевой чекаут, CDEK доставка | backend-dev / devops | **🔴 эскалирован (67 дней)** | Создание заказа через API с фиктивными CDEK-данными; починить прокси/геокодирование | ~~2026-06-23~~ просрочен |
| BLK-010 | 2026-06-22 | YooKassa webhook `payment.succeeded` не приходит на `/api/v1/payments/yookassa/webhook/` в test-окружении. Заказы остаются в `pending` после успешной оплаты до ручной синхронизации или имитации webhook. | P1 | YooKassa интеграция, статусы заказов | devops / project-manager | **🔴 эскалирован (67 дней)** | Ручная синхронизация через API; настроить webhook URL в личном кабинете YooKassa | ~~2026-06-23~~ просрочен |
| BLK-013 | 2026-07-14 | YooKassa E2E-тесты с тестовыми банковскими картами остаются flaky в CI из-за race condition редиректов и нестабильного прохождения 3DS sandbox. Полная стабилизация возможна только после получения реальных YooKassa-ключей и запуска интеграции в прод / полноценном test-окружении. Production-код (`cancellation_reason`) остаётся и работает. | P1 | Задача #65, PR #95, E2E-suite | e2e-tester / project-manager | **🟡 отложено (дедлайн просрочен)** | Закрыть PR #95 без мержа; вернуться к E2E-стабилизации, когда будут реальные ключи | ~~2026-07-21~~ просрочен |
| BLK-014 | 2026-08-29 | Нет production-ключей CDEK — prod-конфиг не настроен (подтверждено пользователем). Когда ключи появятся: (1) `infra/helm/stage/prod/values.yaml` → `env.open`: `CDEK_API_URL: https://api.cdek.ru`, `CDEK_TEST_MODE: "false"` (сейчас prod наследует edu-стенд и test mode из базового values.yaml); (2) переименовать ключи в prod SOPS `SDEK_CLIENT_ID`/`SDEK_CLIENT_SECRET` → `CDEK_ACCOUNT`/`CDEK_SECURE` (backend читает именно их, `config.py:227-228`) или добавить `CDEK_ACCOUNT`/`CDEK_SECURE` в GitHub Secrets (deploy.yml уже прокидывает OVR_); (3) опционально — регистрация webhook-подписки CDEK (`POST /v2/webhooks`), сейчас только polling 15 мин. Prod namespace `promelectron` пока пуст (не задеплоен). Контекст: #190/PR #191. | P1 | CDEK на prod, трек-номера реальных заказов | devops + пользователь (ключи) | **🟡 ждём ключи** | Test работает на edu-стенде; prod не деплоить без этих правок | — |
| BLK-015 | 2026-08-29 | Локальный docker postgres без template DB `promelectron_test_template` — `make test-backend`/`make pre-push` падают с 48 errors `InvalidCatalogNameError` на чистом коде (воспроизведено на задаче toast-follow-scroll, diff frontend-only). Лечится пересозданием template DB (см. backend test helper в `backend/tests/conftest.py`). | P3 | Локальные прогоны backend-тестов, `make pre-push` | backend-dev / devops | **🟡 открыт** | Прогонять только frontend-проверки; CI не затронут | — |
| BLK-016 | 2026-09-13 | deploy-prod невозможен: job использует test-kubeconfig (`vars.KUBECONFIG_PATH` → `/home/aleksandr/.kube/promelectron-test`), SA `promelectron-test-*` без RBAC на secrets в prod-namespace `promelectron` — падение на `harborcred` (run 34758661936). Дополняет BLK-014 (нет prod-ключей CDEK). Issue #256. | P1 | Деплой в prod (вся дизайн-система PR #243–#253 живёт только на test) | devops + пользователь (выбор: prod-kubeconfig vs RBAC) | **🟡 открыт** | — | — |

---

## Эскалированные (>2 дней)

| ID | Дата открытия | Дней открыт | Действие |
|----|---------------|-------------|----------|
| BLK-009 | 2026-06-22 | 67 | Требуется починка CDEK прокси/геокодирования на test-окружении — **нужно решение пользователя** |
| BLK-010 | 2026-06-22 | 67 | Требуется настройка webhook URL в личном кабинете YooKassa — **нужно действие пользователя (доступ к ЛК)** |
| BLK-013 | 2026-07-14 | 45 | Отложено до реальных ключей YooKassa — связано с BLK-010 |

---

## Решённые блокеры

| ID | Дата | Блокер | Severity | Решение | Затраченное время |
|----|------|--------|----------|---------|------------------|
| BLK-012 | 2026-07-11 | Harbor registry `harbor.kubeadm.ru` недоступен с self-hosted runner после обновления железа сервера — deploy pipeline падает на job `build`, не запускаются `test-e2e` / `smoke` / `prod-smoke`. | P0 | Миграция deploy pipeline с Harbor на GitHub Container Registry (`ghcr.io/autonomaco/...`), build job перенесён на `ubuntu-latest`, добавлен job `test` для unit-тестов, обновлён `imagePullSecret` в Helm. Проверено: deploy + E2E на test прошли успешно (run 29155360044). | 1.5 часа |
|----|------|--------|----------|---------|------------------|
| BLK-001 | 2026-05-30 | `.github/` защищена — CI/CD правки требовали ручного доступа | P1 | Доступ предоставлен/решён вручную | — |
| BLK-002 | 2026-05-30 | `worker.enabled=false` в Helm + сломанная команда Celery в K8s | P0 | Worker templates исправлены, Celery работает в K8s | — |
| BLK-004 | 2026-05-30 | `API_BASE_URL` в K8s test окружении не настроен | P1 | Настроен через env/ConfigMap | — |
| BLK-005 | 2026-06-26 | Нет реальных SMTP кредов — email в fallback-режиме | P1 | Креды Yandex SMTP (app password) получены; backend-реализация Phase 1+2 готова в задаче #43/#19. Frontend + Helm values — в работе. | — |
| BLK-006 | 2026-06-02 | Malformed revision ID в Alembic миграции `20260531_222559_guest_order_fields.py` (`revision = 'b1c2d3e4f5a6'`) — некорректная миграционная история | P1 | Пересоздана миграция с корректным revision ID | — |
| BLK-007 | 2026-06-06 | YooKassa test shop отклонял платежи со страницы 'Не сработало' | P1 | Использовать тестовую карту 5555...4477 + проходить 3DS sandbox; платёж проходит, capture работает. Добавлен `completeYooKassaPaymentIfNeeded` в E2E helpers. | 3 часа |
| BLK-008 | 2026-06-22 | `FRONTEND_URL=http://localhost:5173` в `backend/docker-compose.yml` ломает E2E mock-редирект внутри Docker | P1 | Изменить `FRONTEND_URL` и `API_BASE_URL` на `http://frontend:5173` / `http://api:8000` для api/worker/beat в `backend/docker-compose.yml` | 30 мин |
| BLK-011 | 2026-06-22 | Отсутствовали frontend-страницы сброса пароля (`/forgot-password`, `/reset-password`). | P2 | Страницы добавлены, роуты настроены | — |
| BLK-R001 | 2026-05-28 | PostgreSQL enum cleanup — тесты падали | P1 | Добавить `DROP TYPE IF EXISTS roleenum CASCADE` в `conftest.py` + `NullPool` | 4 часа |
| BLK-R002 | 2026-05-28 | E2E checkout timeout — 10 секунд не хватало | P1 | `waitForURL` → `waitForResponse` + `toHaveURL` с 30s | 2 часа |
| BLK-R003 | 2026-05-28 | Rate limiting в CI — `ENVIRONMENT=production` ломал тесты | P1 | Поднять limits для `/login` и `/orders/create` до 50/min | 1 час |
| BLK-R004 | 2026-05-28 | FK violation при seed reset — удаление users ломало suppliers | P1 | Убрать удаление users из `reset_test_state`, оставить только orders/carts | 3 часа |
| BLK-R005 | 2026-05-28 | Email timeout в тестах — SMTP блокировал | P1 | `asyncio.wait_for(..., 5s)` + try/except в `EmailService` | 2 часа |
| BLK-R006 | 2026-05-30 | `frontend/Dockerfile` с `USER nginx` — rollout timed out в CI/CD | P0 | Откат до `3b51d2e`, rebuild через `.dockerignore` | 2 часа |
| BLK-R007 | 2026-05-31 | E2E auth.spec.js ожидал редиректа `/cart` → `/login` после гостевой корзины | P1 | Обновить тест: гость видит корзину, checkout ведёт на login | 1 час |

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
