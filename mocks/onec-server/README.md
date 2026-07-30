# 1C Mock Server (onec-mock)

Standalone-сервис, симулирующий 1С:УНФ для разработки и E2E (Фаза 7 эпика #117, issue #124).
**НЕ** часть `backend/` — играет роль внешней системы и версионируется независимо (D-01/D-14).

Раз в `SYNC_INTERVAL_MINUTES` (по умолчанию 30 мин) сервис собирает неподтверждённые
изменения виртуального каталога, генерирует инкрементальный CommerceML 2.x пакет
(ZIP с `import.xml` + `offers.xml`) и шлёт `POST` на `ONEC_TARGET_URL` с заголовком
`X-1C-Api-Key` (D-02). При 200/202 изменения помечаются отправленными; при ошибке —
retry с backoff (1/5/15 мин, max 3 попытки на тик) и запись в журнал `sent_changes` (D-07).

## Стек

Python 3.12, FastAPI, APScheduler (AsyncIOScheduler) в одном процессе, SQLAlchemy 2.0 async,
PostgreSQL (та же БД, что у backend, отдельная схема `onec_mock`, без Alembic — D-03).
Без Celery/Redis.

## Запуск (dev)

```bash
# полный стек, включая onec-mock (порт 8100)
make dev        # или: docker compose -f backend/docker-compose.yml up -d onec-mock

curl localhost:8100/health/
curl localhost:8100/status/
```

Локально без Docker (PG из compose):

```bash
docker compose -f backend/docker-compose.yml up -d postgres
cd mocks/onec-server
pip install -r requirements-dev.txt
PYTHONPATH=src DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron \
  uvicorn onec_mock.main:app --port 8100
```

## Тесты

Только Docker-PG (схема `onec_mock_test`, drop per test), никогда SQLite:

```bash
make test-onec-mock   # поднимает postgres + pytest из venv
make lint-onec-mock   # ruff
```

## Переменные окружения (D-10)

| Переменная | Default | Описание |
|-----------|---------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron` | Строка подключения (та же БД, что backend) |
| `ONEC_MOCK_DATABASE_URL` | — | Override `DATABASE_URL` для мока (D-03), если задана — имеет приоритет |
| `ONEC_TARGET_URL` | `http://api:8000/api/v1/onec/intake/` | Целевой intake endpoint (D-02) |
| `ONEC_API_KEY` | `dev-onec-api-key` | Ключ `X-1C-Api-Key` (в K8s — из `promelectron-secrets.ONEC_WEBHOOK_API_KEY`). **Default только для локальной разработки** — в compose/K8s ключ всегда приходит из env/секрета |
| `SYNC_INTERVAL_MINUTES` | `30` | Интервал регламентной отправки |
| `SEED_ON_START` | `true` | Заполнить каталог стартовым набором при пустой БД |
| `SEED_PRODUCTS_COUNT` | `200` | Число товаров при seed |
| `CATALOG_SEED` | `42` | Seed детерминированного RNG каталога/сценариев |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
| `ONEC_MOCK_SCHEMA` | `onec_mock` | Имя PG-схемы (тесты используют `onec_mock_test`) |

## Сценарии мутаций (D-06)

| Сценарий | Параметры | Эффект |
|----------|-----------|--------|
| `normal` | — | Цены ±1–5% и остатки у 5–10% товаров |
| `new_products` | `count` (5) | Новые товары с GUID-ами и атрибутами |
| `mass_price_update` | `pct` (10) | Цены всех активных товаров ±pct% (ROUND_HALF_UP, 2 знака) |
| `stock_out` | `share` (0.2) | Обнуление остатков у доли товаров (stock ≥ 0) |
| `delete_products` | `count` (3) | Пометка товаров удалёнными (`ПометкаУдаления` в import.xml) |
| `duplicate_batch` | — | Повторная отправка последнего пакета (те же байты и `X-1C-Batch-Id`) |
| `bad_checksum` | — | Отправка с заведомо неверным `X-1C-Checksum` |

Детерминизм: RNG каждого сценария seeded из `CATALOG_SEED` — воспроизводимость в тестах/E2E.

## API управления (D-08, без auth, только внутренняя сеть)

Trailing slash обязателен во всех endpoint'ах.

- `GET /health/` — healthcheck.
- `POST /trigger/` — форс-отправка pending changes вне расписания.
  Ответ: `{"batch_id": "...", "http_status": 202, "status": "success", "changes_sent": N}`
  или `{"status": "nothing_to_send"}`.
- `POST /scenario/` — тело `{"scenario": "new_products", "params": {"count": 5}, "send_now": true}`.
  Ответ: `{"scenario_run_id": N, "changes_created": M, "batch_id": "..." | null}`.
  Неизвестный сценарий → 422.
- `GET /status/` — состояние планировщика, число pending changes, размер каталога.
- `GET /history/?limit=20&offset=0` — журнал отправок `sent_changes` (limit ≤ 100).

## Деплой (D-09)

- Dev: сервис `onec-mock` в `backend/docker-compose.yml` (build из `mocks/onec-server`).
- K8s: `infra/helm/templates/onec-mock-{deployment,service}.yaml` за флагом
  `onecMock.enabled` (default `false`; test — `true`, prod — `false`). Только ClusterIP,
  ingress НЕ создаётся. Образ собирается CI (`deploy.yml`, `ONEC_MOCK_IMAGE`).

## Контракт отправки (D-02)

`POST {ONEC_TARGET_URL}`, тело — ZIP (`import.xml` + `offers.xml`, CommerceML 2.10,
`СодержитТолькоИзменения="true"`), заголовки: `X-1C-Api-Key`,
`Content-Type: application/xml; charset=utf-8`, `X-1C-Batch-Id: {uuid}`,
`X-1C-Checksum: sha256:{hex}`. Успех = HTTP 200/202.

Генератор пакета — за интерфейсом `PackageGenerator` (`commerceml.py`): точка расширения
под реальный диалект 1С после первой живой выгрузки (D-05).
