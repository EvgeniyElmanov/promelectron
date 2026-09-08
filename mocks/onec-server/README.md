# 1C OData Mock Server (onec-mock)

Standalone-сервис, имитирующий OData API 1С:УНФ поверх реального мартовского дампа
(схема PostgreSQL `onec`: 1523 товара, 31 категория, 82 388 цен, 5 244 остатка,
50 874 значений характеристик, 13 028 файлов-метаданных). Backend ходит в мок **pull-синком** —
мок ничего не отправляет сам (issue #227). **НЕ** часть `backend/` — играет роль внешней
системы и версионируется независимо (D-01/D-14).

## Стек

Python 3.12, FastAPI, SQLAlchemy 2.0 async (asyncpg, NullPool), Pillow (placeholder-изображения).
Без Celery/Redis/APScheduler — сервис read-only поверх схемы `onec`.

## Данные

Сид: `data/onec_seed.sql.gz` (gitignored) — plain SQL схемы `onec`. Восстановление:

```bash
zcat mocks/onec-server/data/onec_seed.sql.gz | docker exec -i promelectron-postgres-1 \
  psql -U postgres -d promelectron   # нужен extension uuid-ossp
```

Мок отдаёт всё содержимое схемы «как настоящая 1С»: цены/остатки/файлы ссылаются и на товары
вне 1523 (дамп — подмножество полного каталога). Sync-код молча пропускает неизвестные товары.

## Запуск (dev)

```bash
# полный стек, включая onec-mock (порт 8100)
make dev        # или: docker compose -f backend/docker-compose.yml up -d onec-mock

curl localhost:8100/health/
curl localhost:8100/status/
curl -u onec:onec "localhost:8100/odata/standard.odata/Catalog_Номенклатура?\$top=2"
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

Только Docker-PG (схема `onec_test`, синтетические фикстуры — сид в тестах не используется),
никогда SQLite:

```bash
make test-onec-mock   # поднимает postgres + pytest из venv
make lint-onec-mock   # ruff
```

## Переменные окружения

| Переменная | Default | Описание |
|-----------|---------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/promelectron` | Строка подключения (та же БД, что backend) |
| `ONEC_MOCK_DATABASE_URL` | — | Override `DATABASE_URL` для мока, если задана — имеет приоритет |
| `ONEC_MOCK_SCHEMA` | `onec` | Имя PG-схемы с данными дампа (тесты используют `onec_test`) |
| `ONEC_MOCK_LOGIN` | `onec` | Basic Auth логин к OData-эндпоинтам (в K8s — из `promelectron-secrets`) |
| `ONEC_MOCK_PASSWORD` | `onec` | Basic Auth пароль. **Default только для локальной разработки** |
| `ONEC_MOCK_BASE_PATH` | `/odata/standard.odata` | Базовый путь OData API |
| `LOG_LEVEL` | `INFO` | Уровень логирования |

## OData API

Base path: `/odata/standard.odata`. Все OData-эндпоинты требуют Basic Auth
(`ONEC_MOCK_LOGIN`/`ONEC_MOCK_PASSWORD`); неверная/отсутствующая пара → 401 с `odata.error`.

Общее:

- Ответ списка: `{"odata.metadata": "<abs base>/$metadata#<Entity>", "value": [...]}`.
- Query-параметры: `$format=json` (игнорируется), `$top` (default 100), `$skip` (default 0),
  `$select`/`$orderby` (игнорируются), `$filter` — подмножество: `<поле> eq '<строка>'`,
  `<поле> eq guid'<guid>'`, `<поле> eq true|false`, соединение через ` and `.
- Неизвестная сущность → 404
  `{"odata.error": {"code": "8", "message": {"lang": "ru", "value": "Сущность '<name>' не найдена"}}}`.
- Нулевой GUID `00000000-0000-0000-0000-000000000000` отдаётся строкой-константой (как 1С).

Сущности (таблица `onec.*` → entity):

| Entity | Таблица | Ключевые поля / фильтр |
|---|---|---|
| `Catalog_КатегорииНоменклатуры` | `categories` | `Ref_Key, Description, Parent_Key`=нулевой GUID, `IsFolder=false, DeletionMark` |
| `Catalog_Номенклатура` | `products` | `Ref_Key, Description, НаименованиеПолное, Артикул, Code, Parent_Key, IsFolder, ТипНоменклатуры, КатегорияНоменклатуры_Key, ЕдиницаИзмерения_Key, Вес=0, DeletionMark`. Фильтр: `ТипНоменклатуры eq 'Запас' and IsFolder eq false` |
| `InformationRegister_ЦеныНоменклатуры` | `prices` | `Period, ВидЦен_Key, Номенклатура_Key, Характеристика_Key, Цена, Актуальность`. Фильтр: `ВидЦен_Key eq '<guid>'` |
| `AccumulationRegister_ЗапасыНаСкладах/Balance` | `stock_balance` | `Организация_Key, Номенклатура_Key, СтруктурнаяЕдиница_Key, КоличествоBalance, КоличествоИнтBalance=0` (остальные *_Key — нулевые GUID). Фильтр: `СтруктурнаяЕдиница_Key eq '<guid>'` |
| `ChartOfCharacteristicTypes_ДополнительныеРеквизитыИСведения` | `attribute_definitions` | `raw` отдаётся как есть; при `raw = NULL` (весь дамп) собирается минимальный record: `Ref_Key, Description, DeletionMark, Заголовок=Description, ValueType=CatalogRef.ЗначенияСвойствОбъектов` |
| `Catalog_ЗначенияСвойствОбъектов` | `attribute_values` | `Ref_Key, Description, Owner_Key, DeletionMark`. Фильтр: `Owner_Key eq '<guid>'` |
| `Catalog_Номенклатура_ДополнительныеРеквизиты` | `product_attributes` | `Ref_Key, LineNumber (строка), Свойство_Key, Значение, ТекстоваяСтрока, Значение_Type`. Фильтр: `Ref_Key eq guid'<guid>'` (обе формы) |
| `Catalog_КлассификаторЕдиницИзмерения` | `units` | `Ref_Key, Description, Code` |
| `Catalog_ВидыЦен` | `price_types` | `Ref_Key, Description, DeletionMark` |
| `Catalog_НоменклатураПрисоединенныеФайлы` | `product_files` | `Ref_Key, Description, ВладелецФайла_Key, Размер (строка), Расширение, DeletionMark, ДатаСоздания`. Фильтр: `ВладелецФайла_Key eq guid'<guid>'` |

Бинарь файла (бинарников в дампе нет — генерируется детерминированный placeholder):

```
GET /odata/standard.odata/Catalog_НоменклатураПрисоединенныеФайлы(guid'<ref_key>')/$value
→ 200, Content-Type: image/jpeg (цветная плашка 320x240 из md5(ref_key))
→ неизвестный guid → 404 odata.error
```

## Management API (без auth, trailing slash)

- `GET /health/` — healthcheck.
- `GET /status/` — счётчики строк по таблицам схемы.

## Структура

```
src/onec_mock/
  config.py   — env-конфигурация (Settings)
  db.py       — async engine/session (NullPool)
  odata.py    — реестр сущностей, сериализаторы, парсер $filter, запросы
  images.py   — детерминированный placeholder JPEG (Pillow)
  main.py     — FastAPI: Basic Auth, OData-роуты, /health/, /status/
tests/
  conftest.py — схема onec_test, синтетические фикстуры
  test_odata.py — контрактные тесты
```
