# E2E CI Lessons Learned — Promelectron

> Записано после многочасовой отладки падения `profile.spec.js` на CI (GitHub Actions self-hosted runner).

---

## 1. Playwright + `node:20-alpine` = `ENOENT` (Chromium not found)

**Ошибка:**
```
Error: spawn /root/.cache/ms-playwright/.../chrome-headless-shell ENOENT
```

**Причина:** `node:20-alpine` использует musl libc. Playwright скачивает glibc-бинарники Chromium, которые не запускаются в Alpine (`ld-linux-x86-64.so.2` отсутствует).

**Решение:** Использовать официальный образ `mcr.microsoft.com/playwright:v1.60.0-jammy` (Ubuntu-based) в `frontend/docker-compose.yml`. В нём Chromium и все системные зависимости уже предустановлены.

**Профилактика:** Никогда не использовать `node:alpine` для Playwright. Только `mcr.microsoft.com/playwright` или `node:20-slim` + `apt-get install` графических библиотек.

---

## 2. Vite 5+ блокирует `Host: frontend` → `403 Forbidden`

**Ошибка:**
```
page.goto: net::ERR_NAME_NOT_RESOLVED at http://frontend:5173/...
```
(после исправления DNS оставался `403 Forbidden`)

**Причина:** Vite 5+ имеет `server.allowedHosts`. По умолчанию разрешены только `localhost`, `127.0.0.1` и IP. При обращении изнутри Docker-сети по hostname `frontend` Vite отвечает `403`.

**Решение:** В `vite.config.js` добавить:
```js
server: {
  host: '0.0.0.0',
  allowedHosts: ['frontend'],
}
```

**Профилактика:** Если frontend в Docker обращается сам к себе или к нему обращаются другие контейнеры по hostname — всегда добавлять этот hostname в `allowedHosts`.

---

## 3. `Date.now()` не уникален в параллельных E2E-тестах

**Ошибка:** `IntegrityError` (unique constraint violation) на email в БД. Приводит к API 500 и остановке на `/register`.

**Причина:** `Date.now()` имеет миллисекундную точность. При `workers=4` на CI несколько тестов могут стартовать в одну миллисекунду и сгенерировать одинаковый email.

**Решение:** Использовать `test.info().workerIndex` (или `Math.random()`) в `uniqueEmail()`:
```js
function uniqueEmail() {
  return `test_${Date.now()}_w${test.info().workerIndex}@example.com`;
}
```

**Профилактика:** Никогда не использовать `Date.now()` в одиночку для генерации уникальных данных в Playwright. Всегда добавлять `workerIndex`, `testIndex` или случайную строку.

---

## 4. `test.describe.configure({ mode: 'serial' })` — dangerous misdiagnosis

**Ошибка:** Тесты в `profile.spec.js` падали стабильно. Было решено сделать их `serial`.

**Последствия:**
- Playwright retry'ит **весь файл целиком**, а не один тест.
- Если первый тест падает, остальные 2 помечаются `did not run`.
- Это **скрыло** настоящую причину (rate limit) и усложнило отладку.

**Решение:** Убрать `serial`. Если тесты независимы (каждый создаёт своего пользователя), они должны выполняться параллельно.

**Профилактика:** `serial` использовать только когда тесты **действительно** зависят от общего состояния (например, один тест создаёт, второй редактирует, третий удаляет). Для изолированных регистраций — только parallel.

---

## 5. Rate limiting (`5/minute`) + Test Environment = стабильный CI failure

**Ошибка:** `profile.spec.js` стабильно падал на регистрации. Страница оставалась на `/register`. Руками регистрация проходила. `auth.spec.js` проходил.

**Корневая причина (root cause):**
1. Test environment на K8s запущен с `ENVIRONMENT=production` (из `infra/helm/values.yaml`).
2. Backend endpoint `/register` имеет `@conditional_limit("5/minute")`.
3. На CI Playwright запускает **~9 тестов с регистрацией параллельно** (`workers=4`).
4. Первые 5 регистраций проходят, 6-я получает `429 Too Many Requests`.
5. API возвращает ошибку → Vue не редиректит → Playwright видит `/register`.
6. `auth.spec.js` проходил, потому что он был в "первой пятёрке" по таймингу. `profile.spec.js` стабильно попадал в "вторую пятёрку".

**Решение:** Поднять rate limit на `/register` до `50/minute` (`backend/src/app/api/users.py`).

**Альтернативы:**
- Запускать E2E с `--workers=1` (медленно).
- Изменить `ENVIRONMENT` в test Helm values с `production` на `test` (тогда `conditional_limit` не применяется).
- Добавить `CI=true` в env API pod (не рекомендуется, т.к. это не CI-окружение).

**Профилактика:**
- Всегда проверять, что test environment не запущено как `production`, если это влияет на rate limiting, logging, debugging.
- При внедрении rate limiting — сразу тестировать E2E на CI с максимальным `workers`.

---

## 6. `os.getenv("CI")` в backend не видит CI runner

**Ошибка:** Было добавлено `and not os.getenv("CI")` в `rate_limiter.py`, но это **не помогло** на test environment.

**Причина:** `CI=true` есть только на GitHub Actions **runner'е**, где запускаются Playwright тесты. Сам backend API работает в **K8s pod**, который не знает о `CI=true`.

**Решение:** Не полагаться на `CI` env variable в backend для отключения rate limiting на test environment. Правильнее — использовать `ENVIRONMENT=test` или поднять rate limit.

**Профилактика:** Разделять логику:
- `CI` — для скриптов, reporter'ов, workflow (на runner'е).
- `ENVIRONMENT` — для backend behavior (rate limits, debug mode, и т.д.).

---

## 7. Fail-fast валидация секретов + placeholder в GitHub Secrets = падение деплоя

**Ошибка:**
```
RuntimeError: ONEC_WEBHOOK_API_KEY must be set to a strong random value in production.
```
Backend-под уходил в CrashLoopBackOff при деплое в `promelectron-test` после merge PR #68 (run 29476928631, 2026-07-16), job `deploy-test` падал, E2E и prod-деплой пропускались.

**Причина:**
1. PR добавил fail-fast валидацию `ONEC_WEBHOOK_API_KEY` при `ENVIRONMENT=production` (`config.py::_load_onec_webhook_api_key`).
2. В GitHub Secrets ключ был задан placeholder-значением `change-me` — по совету `stage/test/secrets.TODO.md`, который утверждал «Backend will not crash in dev/test».
3. Утверждение было неверным: test environment работает с `ENVIRONMENT=production` (см. урок №5), поэтому fail-fast сработал и в test.

**Решение:** Установить сильное значение (`openssl rand -hex 32`) в GitHub Secret `ONEC_WEBHOOK_API_KEY` и передеплоить. TODO-документ исправлен: placeholder для webhook-ключа запрещён в обоих окружениях.

**Сопутствующий эффект:** после падения контейнера рестарты уходили в `ImagePullBackOff` — `registrycred` в кластере создаётся из ephemeral `GITHUB_TOKEN` workflow run'а и умирает вместе с ним. Долгий CrashLoopBackOff, переживший run, превращается в вечный ImagePullBackOff до следующего деплоя.

**Профилактика:**
- Любой новый обязательный секрет: сразу задавать валидное значение в GitHub Secrets **до** merge, в обоих окружениях (один репозиторный секрет используется и для test, и для prod в `deploy.yml`).
- При добавлении fail-fast валидации помнить: test = `ENVIRONMENT=production`, «это проверяется только в prod» — ложное допущение.
- Проверять деплой в test сразу после merge PR, добавляющего новые обязательные env-переменные.

---

## Summary checklist для будущих E2E фич

- [ ] Docker image для E2E — `mcr.microsoft.com/playwright`
- [ ] Vite `allowedHosts` — добавить Docker hostname
- [ ] Уникальные данные — `Date.now() + workerIndex`, не `Date.now()` в одиночку
- [ ] `serial` mode — только для зависимых тестов
- [ ] Rate limits — проверить на CI с `workers=4`
- [ ] `ENVIRONMENT` в test — не `production`, если есть production-only ограничения

---

## 2026-07-30 | onec-universal-intake-0720: новое поле Settings роняет тесты с явными kwargs

**Ошибка:** добавление поля `minio_intake_bucket` в `Settings` (config.py) уронило ~30 тестов (`test_email.py`, `test_auth.py`), которые конструируют `Settings(**kwargs)` с явным списком полей.

**Причина:** тестовые хелперы перечисляют поля Settings вручную; новое обязательное поле dataclass ломает их конструктор.

**Решение:** добавить новое поле в kwargs-хелперы этих тестов (коммит `test(onec): add minio_intake_bucket to Settings kwargs in test helpers`).

**Профилактика:** при добавлении любого поля в `Settings` сразу grep'ать тесты на `Settings(` и обновлять явные kwargs; в перспективе — единая фабрика тестовых Settings.

---

## 2026-07-30 | onec-mock-server-0730: Makefile VENV-путь ломается вне worktree

**Ошибка:** таргеты `test-onec-mock`/`lint-onec-mock` использовали `VENV ?= $(CURDIR)/../../venv` — корректно только из worktree; из корня main-репо venv не находился (finding F002 HIGH на ревью).

**Причина:** Makefile писался и проверялся только из worktree, где venv лежит на два уровня выше; сценарий «после мержа, из корня репо» не проверялся.

**Решение:** `VENV ?= $(shell [ -d $(CURDIR)/venv ] && echo $(CURDIR)/venv || echo $(CURDIR)/../../venv)`.

**Профилактика:** любые пути в Makefile, зависящие от расположения репо, проверять из обоих контекстов (worktree и корень main-репо) — worktree-пайплайн делает это расхождение системным.

---

## 2026-07-30 | onec-mock-server-0730: триггер вне планировщика гоняется с тиком scheduler'а

**Ошибка:** `POST /trigger/` (форс-отправка) мог выполниться параллельно с интервальным тиком APScheduler → двойная отправка одних и тех же pending changes с разными `batch_id` (finding F004 MEDIUM).

**Причина:** два входа в один цикл отправки (scheduler job и HTTP endpoint) без синхронизации.

**Решение:** модульный `asyncio.Lock` в `sender.py`, оба пути (`send_pending`, `resend_last`) целиком под lock.

**Профилактика:** у любого периодического job с ручным триггером сразу закладывать единый lock на критическую секцию; при ревью проверять «сколько входов у этого цикла».

---

## 2026-07-30 | onec-mock: CrashLoopBackOff на test из-за LOG_LEVEL=info (lowercase)

**Ошибка:** после мержа PR #126 деплой в test упал (`UPGRADE FAILED: context deadline exceeded`) — под onec-mock в CrashLoopBackOff: `logging.basicConfig(level='info')` → `ValueError: Unknown level`.

**Причина:** configmap кластера передаёт `LOG_LEVEL: info` (lowercase); в docker-compose дефолт `INFO`, поэтому локальный smoke проблему не поймал. Backend переживает lowercase (обрабатывает уровень иначе), мок — нет: разная обработка одной и той же переменной в разных сервисах.

**Решение:** `log_level.upper()` в `Settings.from_env` + регрессионный тест (PR #128).

**Профилактика:** любой новый сервис, читающий LOG_LEVEL, должен нормализовать регистр; при добавлении сервиса в helm — прогонять `helm template` с реальными stage values и сверять env с ожиданиями кода (не только дефолты compose).

---

## 2026-07-31 | onec-attribute-loader-0731: фиксы ревью сами вносят новые HIGH (итерация 2)

**Ошибка:** фикс F002 (защита от sku-конфликта) реализован линейным сканом `cache.products` на каждый товар → O(N²) на полном импорте 100K (новый HIGH F008); фикс F003 (активация товара первой ценой) реанимировал soft-deleted товар из прошлого прогона, т.к. `cache.deleted` живёт в одном запуске (новый MEDIUM F009).

**Причина:** исправления писались в контексте «закрыть конкретный finding», без повторной оценки производительности и межпрогонных инвариантов (то, что верно внутри одного run, неверно между run'ами).

**Решение:** индекс `cache.skus: dict[str, str]` (O(1) проверка) + активация ценой только «ещё неоценённого» товара (`was_unpriced` до присвоения).

**Профилактика:** каждый фикс ревью проверять двумя вопросами: «как это масштабируется на 100K?» и «что произойдёт на границе прогонов (in-run кэш vs состояние в БД)?»; reviewer на итерациях >1 обязан делать инкрементальное ревью именно фиксов, а не только верификацию.

---

## 2026-07-31 | meilisearch-search-121: healthcheck `localhost` в compose блокирует тесты

**Ошибка:** healthcheck сервиса `meilisearch` в `backend/docker-compose.yml` использовал `localhost:7700/health` — внутри контейнера `localhost` резолвится в `::1`, Meilisearch слушает только IPv4 → `connection refused`, контейнер `unhealthy`, `make test-backend` и `depends_on: service_healthy` блокировались.

**Причина:** wget в alpine-образе Meilisearch по умолчанию идёт на IPv6-loopback.

**Решение:** `127.0.0.1` вместо `localhost` в healthcheck.

**Профилактика:** в healthcheck'ах compose всегда использовать `127.0.0.1`, не `localhost`; после добавления нового сервиса с `depends_on: service_healthy` — прогон `docker compose up` с холодного старта (первый запуск образа может не уложиться в окно healthcheck).

---

## 2026-07-31 | meilisearch-search-121: swap-reindex «вживую» + блокировка event loop job_worker

**Ошибка:** первая реализация `reindex_full` (а) применяла `update_settings` к живому обслуживающему индексу (нарушение D-06 «никогда вживую» — лишняя полная переиндексация прямо перед swap) и (б) вызывала sync Meilisearch SDK прямо в async-функции — event loop job_worker вставал на весь reindex, стопоря CDEK/платежи/intake.

**Причина:** sync SDK выбран осознанно (D-04), но граница sync/async не была проведена явно: async-обёртка написана «снаружи», а длинная цепочка вызовов внутри осталась блокирующей; ensure-index и provision-settings слиплись в одну функцию.

**Решение:** `ensure_index_exists` (get/create, без settings) для serving-индекса отдельно от `provision_index` (settings — только на `products_new`); все sync-вызовы в `reindex_full` через `asyncio.to_thread` + регрессионный тест со spy на `to_thread`.

**Профилактика:** правило «sync SDK в async-коде = каждый вызов через `to_thread`, включая poll-циклы со sleep»; любой код, меняющий index settings, по умолчанию подозрителен на «вживую» — settings только на новом индексе перед swap; partial updates, пришедшие во время reindex, требуют компенсации (watermark + повторный enqueue после swap) — закладывать сразу в дизайн swap-flow.

---

## 2026-08-01 | catalog-filter-panel-122: create-issue создал дубль issue из-за формата task.md

**Ошибка:** `implement-pipeline.py create-issue` не увидел существующий `github_issue: #122` в `task.md` и создал дубль #134, который пришлось закрывать как duplicate.

**Причина:** скрипт парсит строку формата `- github_issue: #N`, а оркестратор записал issue отдельным заголовком `## github_issue` — парсер это не распознал.

**Решение:** в `task.md` связанный issue всегда писать в секции `## GitHub` строкой `- github_issue: #N` (inline-формат, который читает скрипт).

**Профилактика:** перед запуском `create-issue` проверять `grep -n "github_issue:" .agent/runs/<task-id>/task.md`; скрипту полезна валидация «header-style записи» (skill-worthy правка, вынесена в отчёт).

---

## 2026-08-01 | search-api-followups-0801: гонка двух прогонов `make test-backend` → 417 ложных errors

**Ошибка:** developer-субагент оставил свой прогон `make test-backend` в фоне, оркестратор запустил свой поверх — второй прогон упал с 417 errors `template database "promelectron_test_template" does not exist` (122 passed / 417 errors).

**Причина:** тестовый хелпер создаёт per-worker БД из общего template и **дропает template при teardown**; параллельный прогон в том же Docker-PG ловит окно, когда template уже удалён. Повторный одиночный прогон — 539 passed зелёные.

**Решение:** оркестратор перед запуском тестов проверяет отсутствие живых фоновых pytest (`ps aux | grep pytest`) и дожидается/останавливает фоновые прогоны субагентов; developer-субагенту запрещено оставлять фоновые тесты после отчёта.

**Профилактика:** в одном Docker-PG одновременно только один `make test-backend`; если видишь `InvalidCatalogNameError ... template ... does not exist` пачкой — это гонка прогонов, а не регрессия кода: проверь параллельные pytest и перезапусти. С 2026-08-28 прогоны сериализованы механически: `flock` на `TEST_BACKEND_LOCK` в таргетах `test-backend`/`test-onec-mock` (Makefile).

---

## 2026-08-03 | admin-order-modal-details-130: make lint-backend падает из-за расхождения версий ruff (docker 0.16.1 vs проект 0.15.13)

**Ошибка:** `make lint-backend` в worktree падает с 455 ошибками на всём `src/`, хотя изменённые файлы чисты по host ruff 0.15.13.

**Причина:** в docker-образе backend установлен ruff 0.16.1 (новее закреплённого проектного 0.15.13) — новые правила/изменённое поведение дают ошибки на нетронутых файлах (`api/products.py`, `services/cart_service.py`).

**Решение:** отличать pre-existing шум от регрессии: прогонять ruff той же версии, что в проекте, по изменённым файлам diff'а. Задача на выравнивание версии ruff в docker-образе вынесена как tech-debt.

**Профилактика:** если `make lint-backend` внезапно даёт сотни ошибок на чужих файлах — сначала сверь версию ruff в образе (`docker compose exec backend ruff --version`) с проектной, прежде чем чинить код.

---

## 2026-08-03 | admin-order-modal-details-130: красный CI после merge — причиной оказался включённый feature flag на test, а не PR

**Ошибка:** deploy-run для merge #142 упал на `test-e2e / e2e` (6 failed: facet filters ×3, search-filter ×3, checkout Mir ×1). Перезапуск без изменений — тот же результат.

**Причина:** между зелёным прогоном (#140) и нашим кто-то включил на test feature flag `catalog_search_meilisearch` (Redis override `feature:catalog_search_meilisearch=1`). Каталог перешёл на Meilisearch, а индекс не был готов: 7 документов, в `filterableAttributes` нет `attrs.*` → фасеты пустые, UI meilisearch-режима ломал legacy-тесты. Падения совпали по времени с нашим merge, но PR их не вызывал.

**Решение:** выключить флаг через `set_enabled('catalog_search_meilisearch', False)` в pod api → rerun failed jobs → зелёный. Эксперимент подтвердил, что причина — флаг.

**Профилактика:** при красном e2e после merge сначала проверять, какие тесты упали и менял ли их PR; проверять feature flags на окружении (`RedisClient.get('feature:<flag>')`) — facet-тесты в `catalog.spec.js` скипаются при выключенном флаге, поэтому включение флага «оживляет» тесты к неготовому окружению. Включать `catalog_search_meilisearch` на test только после full reindex (`POST /admin/search/reindex/`) и проверки facet-тестов.

---

## 2026-08-03 | fix-search-sort-e2e-143: кастомный ranking rule перед `sort` молча отменяет явную сортировку Meilisearch

**Ошибка:** при включённом `catalog_search_meilisearch` e2e-тест «sort by price ascending» стабильно падал: запрос `search/?sort=price_asc` возвращал товары в порядке убывания остатка, а не цены.

**Причина:** в `RANKING_RULES` кастомное правило `stock:desc` стояло перед `sort`. Meilisearch применяет правила по порядку, поэтому `stock:desc` выигрывал у явного sort-параметра. Unit-тест закреплял ошибочный порядок (`stock:desc < sort`).

**Решение:** `sort` перед `stock:desc` (PR #143). Без sort-параметра `sort` — no-op и `stock:desc` по-прежнему поднимает товары в наличии. После правки rankingRules обязателен full reindex (`POST /admin/search/reindex/`) — settings применяются только при provision во время swap.

**Профилактика:** любое кастомное ranking rule ставить ПОСЛЕ `sort`, если явная сортировка должна побеждать; проверять сортировку живым запросом к Meilisearch, а не только первыми N результатами (первые могут совпасть случайно). E2E-спеки, зависящие от режима каталога, должны probe'ить feature flag (паттерн из `catalog.spec.js`) — `search-filter.spec.js` этого не делал и ломался при переключении флага.

---

## 2026-08-24 | pdp-attributes-sku-stock-0824: root-owned node_modules в worktree ломает `make pre-push` (EACCES rmdir)

**Ошибка:** `make pre-push` в worktree падал на `lint-frontend`: `npm ci` в контейнере (`--user 1000:1000`) — `EACCES: permission denied, rmdir '/app/node_modules/.vite/deps'`, после чистки `.vite` — то же на `@bramus/specificity`.

**Причина:** стадии dev/e2e-окружения, работающие от root, пишут в смонтированный `frontend/` worktree — `node_modules` оказался почти целиком root-овым (~16k файлов). Контейнер с `DOCKER_USER=1000:1000` не может удалить root-файлы.

**Решение:** удалить poisoned-дерево через root-контейнер: `docker compose -f frontend/docker-compose.yml -p promelectron run --rm --user root --entrypoint "" frontend-test rm -rf /app/node_modules /app/.npm`. Диагностика: `find frontend -uid 0 | wc -l`.

**Профилактика:** после прогонов e2e/dev-окружения в worktree проверять `find frontend -uid 0` перед host/container-стадиями с `--user 1000:1000`; по возможности не давать контейнерам root при монтировании исходников.

---

## 2026-08-24 | pdp-attributes-sku-stock-0824: `make test-e2e` локально падает мгновенно и молча (Makefile `\&\&` + SEED_SECRET)

**Ошибка:** `make test-e2e` в worktree падал с `Ошибка 1` через секунду после старта контейнера, без какого-либо вывода тестов.

**Причина:** двойная: (1) в recipe `Makefile:73` внутри `sh -c "..."` стоит `\&\&` — контейнерный sh трактует `\&` как литерал, npm получает `&& npx playwright test` как аргументы и падает; (2) `SEED_SECRET` не пробрасывается в контейнер, а `e2e/global-setup.js` делает fail-fast без него (F006/S001).

**Решение:** запускать эквивалент вручную: `SEED_SECRET=promelectron-test-seed-2024 docker compose -f frontend/docker-compose.yml -p promelectron run --rm --user 1000:1000 -e SEED_SECRET frontend sh -c 'npm install --silent && npx playwright test --workers=1'` (dev-placeholder из `.env.example`, backend в non-production принимает его по умолчанию). Прогон: 114 passed, 4 skipped.

**Профилактика:** Makefile target `test-e2e` требует починки (убрать `\&\&`, добавить `-e SEED_SECRET`) — вынесено как pipeline improvement; до починки использовать ручную команду выше.

---

## 2026-08-24 | pdp-attributes-sku-stock-0824: флаки Admin.spec.js по testTimeout 5s под холодным vite-кэшем

**Ошибка:** два полных контейнерных прогона vitest подряд падали ровно на одном тесте `Admin.spec.js` (каждый раз разном: «не отменяет заказ при отказе в confirm», «в модалке редактирования заказа нет опции „Отменён"») — `Test timed out in 5000ms`.

**Причина:** оба прогона шли сразу после `npm ci` (lint-frontend стадия вайпит node_modules → холодный transform-кэш, 126s transform на весь suite); тяжёлый mount `Admin.vue` под нагрузкой параллельных файлов не укладывался в 5s. К diff задачи отношения нет (Admin.vue не трогали).

**Решение:** диагностика флаки: изолированный прогон `npx vitest run src/__tests__/Admin.spec.js` в том же контейнере — 32/32 за 2.7s; повторный полный прогон с тёплым кэшем — 334/334 за 10.8s. Код не меняли.

**Профилактика:** прежде чем чинить «падающий» тест — прогнать файл изолированно и повторить полный suite с тёплым кэшем; разным падениям разных тестов одного файла под нагрузкой почти всегда соответствует тайминг-флаки, а не регрессия.

---

## 2026-08-24 | product-prices-table: свежий worktree + pre-push = битый node_modules (optional peer + root-owned файлы)

**Ошибка:** `make pre-push` в свежем worktree зависал на E2E: vite падал с `ERR_MODULE_NOT_FOUND: picomatch`, а после ручной починки `docker compose run --user 1000:1000 ... npm install` падал мгновенно и молча.

**Причина:** цепочка из трёх: (1) host `npm ci` (npm на хосте) НЕ ставит optional peer `picomatch`, хотя он есть в lock — vite без него не стартует; (2) контейнерный `npm install` (playwright-образ, root) picomatch доставляет, но создаёт root-owned файлы в примонтированном `node_modules`; (3) последующие `run --user 1000:1000` не могут писать в root-owned директории и падают без вывода (`--silent`).

**Решение:** порядок действий для свежего worktree: host `npm ci` → один прогон `docker run --rm -v $PWD:/app -w /app mcr.microsoft.com/playwright:v1.61.0-jammy npm install --silent` (доставляет optional peers) → `docker run --rm -v $PWD:/app node:20-slim chown -R 1000:1000 /app/node_modules` → дальше E2E ручной командой из урока выше (Makefile `test-e2e` всё ещё сломан: `\&\&` + SEED_SECRET).

**Профилактика:** в `implement-pipeline.py create-worktree` добавить шаг подготовки frontend-зависимостей (npm ci + контейнерный npm install + chown), либо монтировать named volume для node_modules в `frontend/docker-compose.yml`, чтобы контейнерный npm не трогал хостовое дерево. Pipeline improvement.

---

## 2026-08-25 | cart-swipe-delete-mobile: transform на родителе увозит absolute-кнопку действия (swipe-to-delete)

**Ошибка:** на мобильной корзине (<640px) свайп-удаление не работало: после свайпа текст налезал на кнопку «Удалить», а тап по ней вёл в карточку товара.

**Причина:** классическая пара ошибок swipe-to-delete: (1) `transform: translateX(-80px)` вешался на всю карточку `.cart-item`, а кнопка `.cart-item__delete-bg` была её потомком — трансформ смещал и кнопку; (2) у кнопки `z-index: -1` — она оказывалась под съехавшим контентом, и `elementFromPoint` по красной зоне возвращал `.cart-item__name` (с `@click` навигацией). Плюс жест без вертикального порога и без `touch-action: pan-y` конфликтовал со скроллом.

**Решение:** паттерн «подложка — сиблинг, трансформ — на обёртке контента»: `.cart-item__delete-bg` статичный слой `z-index: 0`, контент в `.cart-item__content` (`z-index: 1`, непрозрачный background), трансформ только на обёртку; `touch-action: pan-y` на карточке + игнор жеста при `|dy| > |dx|`. Регрессионные тесты: свайп→тап по подложке → DELETE; вертикальный жест не открывает свайп.

**Профилактика:** swipe-to-delete всегда делать двухслойным (статичная подложка действия + движущийся контент с непрозрачным фоном), никогда не трансформить общего родителя кнопки действия; жесты — с `touch-action` и разделением осей. Проверять вживую через `elementFromPoint`, а не только jsdom (CSS там не применяется).

---

## 2026-08-26 | e2e-mobile-filters: mobile-only коллапс ломает десктопные допущения E2E-спек

**Ошибка:** после мержа mobile-low-fixes (#174, фильтры каталога свёрнуты на <768px) deploy-прогоны main падали на 5 E2E-спеках (catalog facet ×4, search-filter price range) — таймаут ожидания `[data-testid="filter-panel"]`.

**Причина:** Playwright E2E бегает на viewport **390×844** (`frontend/playwright.config.js`), т.е. мобильные стили/поведение применяются во всех E2E. Спеки писались в десктопном допущении «панель фильтров видима сразу». Два вторичных грабли хелпера: `<details>` с панелью рендерится async (после ответа /search/ с фасетами) — без waitFor attached хелпер выходил до появления элемента; `details.locator('summary')` матчит и вложенные summary FilterPanel — нужен `:scope > summary`.

**Решение:** хелпер `openFiltersPanel(page)` в `e2e/helpers.js`: waitFor attached → если не open, клик по `:scope > summary` → waitForFunction open; вызывать после goto перед работой с фасетами.

**Профилактика:** любая фича «на мобилке иначе» (коллапсы, бургер-меню, bottom-nav) должна сразу ревьюиться на предмет влияния на E2E — спеки бегают на мобильном viewport. Хелперы для mobile-состояний класть в `e2e/helpers.js` в момент фичи, а не post-mortem.

---

## 2026-08-26 | серия мержей mobile-*: параллельные deploy-прогоны гоняются на общем test-окружении

**Ошибка:** три deploy-прогона main подряд (после мержей #170, #173, #174) показали разные наборы падающих E2E (auth guest-cart merge, cdek-widget, checkout-failed-cards и др.), не воспроизводимые при локальном прогоне против того же test-окружения.

**Причина:** каждый мерж редеплоит общее тестовое окружение; E2E-стадия более раннего прогона фактически бежала уже против кода более позднего мержа + seed одного прогона менял данные под другим. Падения — гонки окружения, а не регрессии.

**Решение:** перед разбором падений deploy-прогона проверить, не было ли параллельного/следующего редеплоя; детерминированные падения (одни и те же спеки во всех прогонах) отделять от гонок (разный набор, не воспроизводится локально).

**Профилактика:** при серии мержей в main мержить по одному и дожидаться зелёного deploy-прогона перед следующим; настроить concurrency-группу на deploy-workflow (cancel-in-progress) — pipeline improvement.

---

## 2026-08-26 | restore-cart-select-items-177: коммит из устаревшего working tree молча откатывает чужую фичу (второй случай)

**Ошибка:** фича #61 (выбор товаров в корзине, PR #62, `fe6f0f9`) была полностью вмерджена, а на следующий день коммит `41a5043` («chore(agent): audit and fix agent pipeline…») молча вернул старые версии файлов — backend фичи исчез из main целиком (модель без колонки `selected` при живой миграции `9614c59dd5a3` → drift схема/модель, фронт звал несуществующий endpoint). Обнаружено только ревизией закрытых spec-issue спустя ~7 недель. Это второй случай того же класса: 2026-08-19 коммит `7a89c8d` восстановил старые файлы из PyCharm Local History поверх закоммиченных.

**Причина:** коммит собирается из устаревшего working tree (не сделан `git pull`/`git status` перед add) или из IDE Local History; diff против main никто не смотрит пост-фактум — зелёный CI не сигнализирует об «исчезнувшей» фиче, т.к. тесты фичи удаляются тем же коммитом.

**Решение:** восстановление адаптивным переписыванием по спеке + `git show fe6f0f9` как референс (НЕ cherry-pick — main ушёл вперёд: product_prices, Recipient v1, #111). Drift «миграция есть, колонки в модели нет» чинится возвратом колонки в модель без новой миграции (верификация: `alembic check` без diff по этой колонке).

**Профилактика:** (1) перед любым «хозяйственным» коммитом, собранным не через worktree-пайплайн, — `git status` + осмотр `git diff --stat` на предмет удалений чужого кода/тестов; (2) периодическая ревизия закрытых spec-issue «спека закрыта ≠ реализовано» (проверка кода, а не статуса на борде) — вошло в практику 2026-08-26; (3) drift-детектор: сделать `alembic check` зелёным (сейчас он всегда красный от pre-existing drift и потому бесполезен) — отдельная задача.

---

## 2026-08-27 | infra-test-e2e-concurrency-179: `frontend-test` в `make test-e2e` вайпит node_modules и гоняется с dev-server/playwright

**Ошибка:** после починки `\&\&` и SEED_SECRET `make test-e2e` падал дважды подряд: сначала `vite: not found` у dev-server'а `frontend`, затем молчаливый exit 243 (EACCES) у playwright-раннера.

**Причина:** `$(COMPOSE) up -d` поднимал и сервис `frontend-test`, чей entrypoint — `npm ci` в примонтированный `frontend/` worktree. `npm ci` полностью пересоздаёт `node_modules`: (1) гонка с dev-server'ом — vite теряет свой бинарник посреди работы; (2) `npm ci` идёт от root → `node_modules` становится root-owned → последующие `run --user 1000:1000` (playwright) не могут писать и падают без вывода. Тот же класс проблемы, что в уроках 2026-08-24 (root-owned node_modules, битый node_modules в свежем worktree).

**Решение:** в `test-e2e`/`test-visual` поднимать явный список сервисов (`postgres redis minio meilisearch api job-worker onec-mock frontend`) без `frontend-test`; playwright бежит отдельным `run --rm --user 1000:1000 -e SEED_SECRET frontend`. SEED_SECRET в Makefile резолвится из `.env`/`../../.env` с fallback на dev-placeholder из `.env.example` (корневой `.env` его обычно не содержит).

**Профилактика:** никогда не поднимать сервисы с `npm ci`/установкой зависимостей в общем `up -d` рядом с long-running процессами, использующими тот же примонтированный `node_modules`; установка зависимостей — только явным отдельным шагом (см. `_prepare_frontend_deps` в `scripts/implement-pipeline.py`), после неё — `chown 1000:1000`.

---

## 2026-08-27 | fix-alembic-check-drift-183: зелёный alembic check — model-to-schema без новых миграций

**Ошибка:** `alembic check` годами был красным от pre-existing drift (6 пунктов: `categories.is_active`, nullable в cdek-таблицах, unique constraints vs `unique=True`, лишний `index=True` на `EmailVerificationToken.user_id`), поэтому реальный drift тонул в фоновом шуме.

**Причина:** миграции выражали исходное намерение (явные `NOT NULL`, явные `UniqueConstraint`, осознанный набор индексов), а модели писались позже «на глаз» и не догнали схему.

**Решение:** во всех пунктах правим модели под схему (model-to-schema), DDL на prod не нужен. Ключевые технические факты: (1) alembic не сравнивает **unnamed** UniqueConstraint — в модели constraint'ы надо объявлять в `__table_args__` с **точными PG-автоименами** (`<table>_<col>_key`), тогда они матчатся с реальными и drift уходит без миграций; (2) `unique=True` на колонке ≡ unique index `ix_*`, а в БД был constraint + неуникальный индекс — семантически эквивалентно, но autogenerate видит разницу; (3) standalone `index=True`, покрытый composite-индексом (leftmost prefix), — источник ложного drift, удалять из модели, а не добавлять миграцией.

**Профилактика:** `make migrate-check` добавлен в Makefile; `alembic check` стал обязательным шагом QA (`qa/SKILL.md`, `qa-gate/SKILL.md`) и чекбоксом в `pre-edit-checklist.md` для задач, трогающих `backend/src/app/models/` или `backend/alembic/`. Красный check теперь = реальный drift, игнорировать нельзя.

---

## 2026-08-28 | fix-cdek-tracking-number (#190): INVALID-заказ CDEK — вечный polling и невидимая ошибка

**Ошибка:** «не приходит трек-номер от СДЭКа после отправки». Диагностика: CDEK отклонил заказ (`INVALID`, несуществующий ПВЗ из тестовых данных), `cdek_number` не присваивается никогда, а `CDEK_SYNC_ORDER_STATUS` перепланировался бесконечно — ошибка не была видна ни покупателю, ни админу. Happy path при этом работал (валидный заказ на edu-стенде получает `cdek_number` за ~20 с — проверено прямым вызовом API).

**Причина:** два слоя конфиг-ловушки: (1) `INVALID` не входил в `CDEK_TERMINAL_STATUSES`; (2) значение этого списка дублируется в **5 местах** (config.py default, backend/.env.example, корневой .env.example, docker-compose.yml, helm values) — правка default в config.py ничего не меняет, если env задан явно. Ревью поймало пятую копию, выпавшую из плана.

**Решение:** явная ветка `INVALID` в `handle_cdek_sync_status` (`sync_failed=True`, стоп reschedule) — независимо от env-конфига; `INVALID` добавлен во все 5 копий `CDEK_TERMINAL_STATUSES`; cron не подбирает `sync_failed=True`. Регрессионные тесты падали до фикса.

**Профилактика:** (1) любой новый терминальный/ошибочный статус внешнего API — сразу решать, как он попадает в terminal-список и как виден админу, «молчаливый retry forever» недопустим; (2) при изменении env-default искать ВСЕ копии значения (`grep -rn` по всему репо, включая корневой .env.example), а не только в backend/ и infra/; (3) диагностику интеграций начинать с данных (таблица `cdek_orders` + прямой вызов API провайдера) — это сразу отделяет «код сломан» от «окружение/данные».

---

## 2026-08-29 | toast-follow-scroll (#194): `overflow-x: hidden` на html/body ломает `position: sticky` всех потомков

**Ошибка:** toast-уведомления не следовали за скроллом. Тосты якорятся к хедеру (`.header__toast`, `position: absolute` под ним), а хедер с `position: sticky; top: 0` на деле уезжал вверх вместе со страницей.

**Причина:** `overflow-x: hidden` на `html` и `body` (`frontend/src/assets/base.css`) делает их scroll-контейнерами и ломает `position: sticky` для всех потомков — известный CSS-подводный камень. Sticky в `Header.vue` был написан, но молча не работал. Воспроизводится только в реальном браузере (jsdom не делает раскладку): scrollY=1500 → `header.getBoundingClientRect().top === -1500`.

**Решение:** `overflow-x: clip` с fallback-строкой `overflow-x: hidden` перед ней (Safari < 16 отбросит clip и останется на старом поведении без регресса). `clip` не создаёт scroll-контейнер, sticky восстанавливается. Регрессионный тест — только Playwright (unit в jsdom бессмыслен для sticky): `frontend/e2e/toast-follow-scroll.spec.js`, падает до фикса, зелёный после.

**Профилактика:** (1) при нетривиальном `overflow` на `html`/`body` помнить, что любой `sticky` ниже по дереву молча сломается — проверять в браузере, а не по коду; (2) CSS-раскладочные баги (sticky, fixed, viewport) покрывать E2E, а не unit-тестами; (3) в toast-тестах Playwright `click()` auto-scroll'ит элемент в viewport и отменяет тестовый `scrollTo` — для сценариев «из глубины страницы» использовать DOM-click через `evaluate` + ассерт `window.scrollY > 0`.

---

## 2026-08-29 | fix-cdek-order-number-collision (#195): reseed БД + внешний стенд = коллизия бизнес-идентификаторов

**Ошибка:** после E2E-reseed БД на test новые заказы падали в CDEK со статусом INVALID (`error_validate_im_dep_number_has_already_had_integration`) и не получали трек-номер, хотя данные заказа (ПВЗ, тариф, получатель) были валидны.

**Причина:** внешние системы переживают reseed нашей БД. Мы слали `number = str(order.id)` как «номер заказа ИМ», а CDEK требует его уникальности среди активных заказов аккаунта. Стенд не удаляет старые заказы → id, начавшиеся заново с 1, коллидируют с прошлыми заказами. Причина видна только в `requests[].errors` ответа `GET /v2/orders/{uuid}` — статус INVALID сам по себе причину не содержит.

**Решение:** `number = f"PM-{order.id}-{uuid4().hex[:6]}"` — уникально независимо от reseed и повторных отправок; webhook-fallback извлекает id из формата, legacy-ветки сохранены. Регрессионные тесты падали до фикса.

**Профилактика:** (1) любой идентификатор, уходящий во внешнюю систему с uniqueness-констрейнтом, не должен быть голым автоинкрементным id — добавлять namespace/suffix; (2) при статусе INVALID/ошибке от внешнего API первым делом смотреть `requests[].errors` (или аналог) провайдера, а не гадать по коду; (3) помнить, что E2E-seed сбрасывает только нашу БД — внешние стенды копят мусор и влияют на последующие прогоны.

---

## 2026-08-29 | cart-button-state (#198): удаление тостов ломает e2e-хелперы за пределами очевидных спек

**Ошибка:** фича удалила success-тосты корзины/избранного; spec учёл 3 e2e-спеки с ожиданием `.toast--success` (catalog, pdp, cdek-widget), но review поймал ещё две — `checkout.spec.js` и `checkout-failed-cards.spec.js` (хелпер `addFirstProductToCart`), которые упали бы в CI на golden path.

**Причина:** ожидание тоста пряталось в локальных хелперах e2e-спек, а не в самих тестах; точечный прогон разработчика покрывал только изменённые файлы, поэтому 11 passed ничего не говорили про checkout-suite.

**Решение:** замена ожидания на проверку состояния кнопки (`toContainText('В корзине')`) во всех 5 спеках; блокер пойман на code review (F001), исправлен и VERIFIED.

**Профилактика:** (1) при удалении любого UI-элемента с testid/классом грепать ВЕСЬ `frontend/e2e/` по селектору и по тексту, включая хелперы (`e2e/helpers.js` и локальные функции спек), а не только очевидные спеки; (2) точечный e2e-прогон должен включать все спеки, которые нашёл grep, а не только отредактированные; (3) при host-прогонах Playwright экспортировать `API_URL=http://localhost:8000` — без него хелперы, дёргающие API напрямую (`setYooKassaPaymentStatus`), падают с `Invalid URL`.

---

## 2026-08-29 | implement-pipeline cleanup: молчаливый `rmtree(ignore_errors=True)` копил осиротевшие worktree

**Ошибка:** `implement-pipeline.py cleanup` рапортовал «Cleaned up», но каталоги `.worktrees/<task-id>` оставались на диске (~1.6 ГБ на 6 задач): root-owned `__pycache__`/`node_modules` из docker-прогонов ломали `git worktree remove` и `shutil.rmtree(..., ignore_errors=True)`, а ошибка глоталась.

**Причина:** `ignore_errors=True` + отсутствие post-check «каталог действительно исчез» + `git worktree remove` не удаляет незарегистрированные каталоги.

**Решение:** новый `_remove_tree()` — явный rmtree без ignore_errors, при PermissionError fallback на docker chown (`node:20-slim`, тот же паттерн, что в `_prepare_frontend_deps`), затем повтор; `_cleanup_task`/`cmd_cleanup`/janitor возвращают/проверяют факт удаления и печатают WARNING/CLEANUP_INCOMPLETE вместо ложного успеха. Проверено на каталоге с root-owned файлами.

**Профилактика:** (1) cleanup-операции всегда верифицировать post-condition («цели больше нет»), никогда не доверять коду возврата при ignore_errors/check=False; (2) всё, что docker пишет в bind-mount worktree, должно завершаться chown на uid пользователя — иначе следующий cleanup снова споткнётся.

---

## 2026-09-11 | kimi-skills-thin-wrappers (#234): миграция на указатели молча меняет поведение команд

**Ошибка:** при переводе `.kimi-code/skills/qa/SKILL.md` на обёртку-указатель (`.agents/agents/qa.md`) канонические команды роли подменились: `make test-backend` (flock) → `uv run pytest`, локальный E2E (make dev) → E2E против test-окружения. В ship потерялась обработка bare task-id — главный вызов из implement. Поймано только code review (F-001/F-002), не компиляцией.

**Причина:** общий файл и копия разошлись не только формулировками, но и процедурными командами; указатель молча наследует ВСЁ из цели, включая то, что раньше было переопределено в копии.

**Решение:** ревью-чек-лист «поведенческий дифф»: при замене файла на указатель сверять не текст, а исполняемые команды и процедурные стопы (grep по `make |uv |npm |npx |gh |helm ` в старой и новой цепочке «обёртка → цель»).

**Профилактика:** (1) любая миграция docs→pointer требует сравнения команд, а не только смысла; (2) решения о смене контура проверки (локально vs test env) выносить владельцу явно (H-item), а не наследовать молча.

---

## 2026-09-14 | уборка после мержа: удалена чужая ветка `docs` вместе со своими

**Ошибка:** при пост-мерж уборке дизайн-системы (PR #209 + этапы 1–3) в список удаления попала ветка `docs` — источник PR #209, автор коллега. Удалена локально и на origin. Восстановлена по `headRefOid` из `gh pr view 209` (SHA `77344ec`), содержимое не пострадало (squash-мерж в main).

**Причина:** список веток на удаление формировался по паттерну «ветки этой задачи», без проверки авторства и того, чья это ветка; ветка коллеги совпала по теме (тот же PR #209) и была удалена «заодно».

**Решение:** восстановление через `gh pr view <N> --json headRefOid` → `git branch docs <sha>` → `git push origin docs`. Tip ветки точно совпал с состоянием на момент мержа.

**Профилактика:** (1) перед удалением ЛЮБОЙ ветки проверять авторство (`git log -1 --format='%an'`) и связь с чужим PR (`gh pr list --head <branch> --state all`); чужие ветки не удалять никогда — только свои `feature/<task-id>` из текущего пайплайна; (2) ветки, смерженные squash, формально «unmerged» — это не повод считать их мусором, если автор не ты; (3) при сомнении — спросить владельца, удаление из origin необратимо без точного SHA.
