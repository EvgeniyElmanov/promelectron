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

## Summary checklist для будущих E2E фич

- [ ] Docker image для E2E — `mcr.microsoft.com/playwright`
- [ ] Vite `allowedHosts` — добавить Docker hostname
- [ ] Уникальные данные — `Date.now() + workerIndex`, не `Date.now()` в одиночку
- [ ] `serial` mode — только для зависимых тестов
- [ ] Rate limits — проверить на CI с `workers=4`
- [ ] `ENVIRONMENT` в test — не `production`, если есть production-only ограничения
