# Универсальный intake-эндпоинт 1С (Фаза 1, #118)

`POST /api/v1/onec/intake/` — приём произвольных выгрузок 1С «как есть».
Тело сохраняется байт-в-байт в объектное хранилище (MinIO, бакет `onec-intake`),
метаданные — в PostgreSQL (`onec_intake_log`). Формат тела НЕ парсится и НЕ валидируется.

## Запрос

- **URL:** `https://<api-host>/api/v1/onec/intake/` (trailing slash обязателен)
- **Метод:** `POST`
- **Заголовки:**

  | Заголовок | Обязательность | Описание |
  |-----------|----------------|----------|
  | `X-1C-Api-Key: <секрет>` | обязательный | Тот же ключ, что и для `/onec/webhook/` |
  | `X-1C-Checksum: sha256:<hex>` | опциональный | SHA256 от тела запроса (префикс `sha256:` обязателен по контракту мока; голый hex тоже принимается). При несовпадении — `400`, запись в `onec_intake_log` со `status=failed`, job разбора НЕ создаётся. Без заголовка проверка не выполняется |
  | `X-1C-Batch-Id: <uuid>` | опциональный | Идентификатор пакета 1С. Сохраняется в `onec_intake_log.headers` для корреляции; **дедупликация по нему НЕ выполняется** (см. ниже) |
  | `Content-Type` | опциональный | Любой (`application/json`, `application/xml`, `application/zip`, `application/octet-stream`, …); может отсутствовать |

- **Тело:** любое — OData JSON, CommerceML XML, ZIP, бинарные данные. Пустое тело (0 байт) допустимо.

## Ограничения

- **Максимальный размер тела: 100 МБ.** При превышении — `413 Payload Too Large`,
  ничего не сохраняется. Выгрузки больше 100 МБ отправляйте частями.
- **Rate limit:** 100 запросов/минуту на эндпоинт.

## Ответы

| Код | Значение |
|-----|----------|
| `202 Accepted` | Принято. Тело: `{"intake_id": "<uuid>", "received_bytes": <int>}` |
| `400 Bad Request` | `X-1C-Checksum` не совпал с SHA256 тела (или заголовок malformed). Сырое тело сохранено в MinIO, в `onec_intake_log` — `status=failed` + `error`, job разбора не создан |
| `401 Unauthorized` | Отсутствует или неверен `X-1C-Api-Key` |
| `413 Payload Too Large` | Тело больше 100 МБ |

`202` означает только факт приёма и сохранения; разбор формата выполняется
отдельно (Фаза 4). `intake_id` используйте при разборе инцидентов.

## Решение по `X-1C-Batch-Id`: дедупликация НЕ выполняется (#162)

Сознательный отказ от dedup по batch id, в отличие от `/onec/webhook/`:

- `/webhook/` дедуплицирует по `batch_id`, потому что webhook **сразу** создаёт
  `onec_change_log` + job `ONEC_APPLY_CHANGES` (обработку), а `batch_id` там —
  обязательное поле структурированного payload с unique-ограничением в БД.
- `/intake/` — **сырой журнал приёма**: его назначение — фиксировать каждую
  отправку байт-в-байт, включая повторные (сценарий мока `duplicate_batch` —
  ценная диагностическая информация, а не шум).
- Разбор intake-файлов идемпотентен (upsert по `onec_id` в `onec_intake_loader`),
  поэтому повторный пакет безопасен для каталога.
- `batch_id` при этом не теряется: заголовок сохраняется в
  `onec_intake_log.headers` (JSONB) и доступен для корреляции при инцидентах.

## Обработка (Фаза 4, #120)

`job_worker` забирает job `ONEC_INTAKE_PROCESS`, скачивает файл из MinIO и
разбирает его по `docs/onec/FORMAT_MAP.md` (upsert по `onec_id`, идемпотентно).
Результат — в `onec_intake_log.status`: `parsed` (успех) или `failed` (+ поле
`error`); счётчики разбора — в `processing_log` соответствующего job'а.
После разбора ставится job `SEARCH_INDEX_PRODUCTS` на затронутые товары —
его handler появится в Фазе 5 (эпик #117); до тех пор такие job'ы падают с
`Unknown job_type`, это осознанно принятое поведение.

## Пример

```bash
curl -X POST "https://api.promelectron-test.aidrivencode.ru/api/v1/onec/intake/" \
  -H "X-1C-Api-Key: $ONEC_WEBHOOK_API_KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @export.zip
# => {"intake_id":"3f6f…","received_bytes":1048576}
```
