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

После `npm install` в контейнере файлы в bind-mounted `node_modules` остаются root-owned. Пайплайн чинит владельца без sudo — chown в контейнере `node:20-slim` (`implement-pipeline.py` `_prepare_frontend_deps`): `docker run --rm -v "$PWD/frontend:/app" node:20-slim chown -R "$(id -u):$(id -g)" /app/node_modules`.

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

## 13. Фронтенд читает поле, которого нет в response schema

`ProductCard` инициализировал `isFavorite` из `props.product.is_favorite`, но вложенный `product` в `GET /favorites/` — это `ProductOut` без этого поля (оно только в `ProductDetailOut`). Итог: `undefined → false`, клик по сердечку шёл в `POST add` вместо `DELETE` → 400, товар «не удалялся» (#188, PR #189). Профилактика: когда фронтенд зависит от пер-юзерного поля (`is_favorite`, `in_cart`), сверяйся с конкретной response-схемой эндпоинта, а не с «соседней»; признак такого бага — тихая деградация в `false`/`undefined` без ошибок в консоли.

## 14. Точечный `kubectl apply` до мержа ломает первый `helm upgrade`

Ресурс, созданный в обход Helm (`kubectl apply` из рендера чарта для проверки на живом окружении), не имеет ownership-метаданных — первый `helm upgrade` после мержа падает: `cannot be imported into the current release: missing app.kubernetes.io/managed-by / meta.helm.sh/release-*` (#212, run 36566242605). Профилактика: при точечном apply сразу ставь `app.kubernetes.io/managed-by: Helm` + `meta.helm.sh/release-name/release-namespace` (или apply через `helm template | kubectl apply` с этими метаданными). Лечение без передеплоя: `kubectl annotate`/`label` на живом объекте, затем `gh run rerun --failed`.

---
