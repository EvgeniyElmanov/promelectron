---
name: known-pitfalls
description: >
  Real pitfalls that have already happened in Promelectron. Check before committing.
type: prompt
disableModelInvocation: true
---

# Known pitfalls (Promelectron)

> Реальные проблемы, которые уже случались. Проверь перед коммитом.

## 1. Tests must not touch dev/prod DB

`conftest.py` использует отдельную тестовую базу данных. Всегда запускай `make test-backend` (PostgreSQL in Docker), никогда `pytest` локально на SQLite.

## 2. Rate limiting ломает тесты

Сбрасывай limiter в фикстуре `client`.

## 3. SQLite ≠ PostgreSQL

Foreign keys, unique constraints и SQL syntax отличаются. Тестируй на PostgreSQL.

## 4. Trailing slash in FastAPI

`api.get('/categories/')` matchится с `@router.get("/")`. Отсутствие trailing slash вызывает 307/CORS проблемы.

## 5. Права доступа Docker `node_modules`

После `npm install` в контейнере почини владельца: `sudo chown -R $(whoami):$(whoami) frontend/node_modules`.

## 6. Бит исполняемости `docker-entrypoint.sh`

Запусти `chmod +x backend/docker-entrypoint.sh` перед стартом.

## 7. `docker-entrypoint.sh` игнорирует аргументы

Используй `--entrypoint ""` для one-off команд: `docker compose run --rm --entrypoint "" api alembic upgrade head`.

## 8. Vite proxy hostname в Docker

Используй имя сервиса: `proxy: { '/api': { target: 'http://api:8000', changeOrigin: true } }`.

## 9. Версия Alembic без таблиц

Если `drop_all` удалил таблицы, но `alembic_version` осталась, выполни `DELETE FROM alembic_version;`, затем `alembic upgrade head`.

## 10. Дублирующий route без guard

Оставляй только одно определение route с правильными `meta` guards.

## 11. Path traversal в имени файла

Санитизируй имена файлов через `os.path.basename` и проверки `os.path.realpath`.

## 12. Красный CI без изменения кода — проверь feature flags

Если e2e внезапно упал, а diff PR эти зоны не трогает, сначала проверь feature flags на окружении: `RedisClient.get('feature:<flag>')` в pod api. Флаги, меняющие backend-путь (как `catalog_search_meilisearch`), включают «спящие» e2e-тесты и новый UI — без готового окружения (миграции, индекс, данные) они краснеют. Перед включением такого флага: подготовь окружение → прогони зависимые e2e → только потом включай.

---
