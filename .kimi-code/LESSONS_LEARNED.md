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
