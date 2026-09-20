# Бэклог Promelectron — указатель

> ## ⚠️ Источник истины — GitHub Issues, не этот файл
>
> План работ живёт в открытых issue на `AutonomaCo/promelectron`, витрина — `ai-launcher/BOARD.md`.
> Этот файл — **указатель и историческая запись спринтов**: он показывает, что было, и куда
> уехало живое. Если он расходится с GitHub, прав GitHub.
>
> Посмотреть бэклог: `/backlog-list` · пульт запуска: `/board` · что запускать сейчас: `/sessions`
>
> Свёрнут 2026-09-03 после сверки каждого пункта с кодом: 12 задач числились открытыми, будучи
> сделанными или отменёнными, а 16 настоящих не были заведены нигде.

---

## Открытое — в GitHub

| Issue | Что | Замок | Приоритет |
|---|---|---|---|
| [#210](https://github.com/AutonomaCo/promelectron/issues/210) | вебхук ЮKassa принимает неподписанные запросы и не сверяет сумму | `backend` | **P0** 🔴 |
| [#211](https://github.com/AutonomaCo/promelectron/issues/211) | цена доставки берётся из тела запроса без валидации | `backend` | **P0** 🔴 |
| [#212](https://github.com/AutonomaCo/promelectron/issues/212) | резервного копирования БД нет вообще | `infra` | **P0** 🔴 |
| [#213](https://github.com/AutonomaCo/promelectron/issues/213) | боевой `ONEC_WEBHOOK_API_KEY` в git и совпадает с тестовым | `infra` | **P0** 🔴 |
| [#214](https://github.com/AutonomaCo/promelectron/issues/214) | prod в песочнице СДЭК + 2 реплики при локальном хранилище | `infra` | **P0** |
| [#215](https://github.com/AutonomaCo/promelectron/issues/215) | на pull request не гоняется ни одна проверка | `infra` | **P0** |
| [#216](https://github.com/AutonomaCo/promelectron/issues/216) | смена статуса заказа админом всегда 404 | `backend` | P1 |
| [#217](https://github.com/AutonomaCo/promelectron/issues/217) | миграции применяются дважды, падение глушится | `backend` | P1 |
| [#218](https://github.com/AutonomaCo/promelectron/issues/218) | поды от root, PostgreSQL через NodePort наружу | `infra` | P1 |
| [#219](https://github.com/AutonomaCo/promelectron/issues/219) | боевые секреты: SOPS неполный, OAuth в GitHub Secrets | `infra` | P1 |
| [#220](https://github.com/AutonomaCo/promelectron/issues/220) | rate limit по IP пода, гостевой заказ без лимита | `backend` | P1 |
| [#221](https://github.com/AutonomaCo/promelectron/issues/221) | debug-эндпоинты платежей в продовом роутере | `backend` | P1 |
| [#222](https://github.com/AutonomaCo/promelectron/issues/222) | наблюдаемости нет: ни Sentry, ни метрик, ни логов | `infra` | P1 |
| [#223](https://github.com/AutonomaCo/promelectron/issues/223) | нет индексов на горячих внешних ключах | `backend` | P1 |
| [#224](https://github.com/AutonomaCo/promelectron/issues/224) | спека оплаты зеленеет, ничего не проверив | `e2e` | P1 |
| [#225](https://github.com/AutonomaCo/promelectron/issues/225) | доступность: модалки без `role`, фокус-трапа и Escape | `frontend` | P1 |
| [#186](https://github.com/AutonomaCo/promelectron/issues/186) | флаки `cart-select.spec.js` — протечка состояния корзины | `e2e` | P1 |

Метка зоны на issue **и есть** его замок. Правила — `ai-launcher/CONVENTIONS.md`.

---

## Не заведено: P2-долг

Подтверждён кодом при сверке 2026-09-03, но ждёт разгребания верха. Заводить по мере
освобождения рук — `/backlog-add`.

| Что | Замок | Доказательство |
|---|---|---|
| Мёртвая ветка гостевого чекаута: 563 строки вью + 2 спека на недостижимом коде (бэкенд отвечает 410) | `frontend` | `views/GuestCheckout.vue:283`, `api/orders.py:50-68` |
| Протечка состояния в `admin.spec.js` (класс #186) + 31 `waitForTimeout` в спеках | `e2e` | `admin.spec.js:71,77,90` |
| Мёртвый `delivery_methods`: 4 живых эндпоинта, никем не вызываются, деньги во `Float` | `backend` | `models/delivery_method.py:15` |
| Образ backend: нет `.dockerignore`, dev-зависимости в рантайме, нет кеша сборки | `infra` | `backend/Dockerfile:7` |
| Дубли: `loadSupplierCityCode` ×2, магическое `44` ×6, `PHONE_REGEX`/`NAME_REGEX` ×3 | `frontend` | `Cart.vue:431`, `GuestCheckout.vue:189` |
| Крупные компоненты без тестов: `ProductFormModal` (510), `UserDetailsModal` (469), `AddressForm`, `useAddressSuggestions` | `frontend` | — |
| `console.error` ×5 в проде + lazy loading для 30 статически импортируемых view | `frontend` | `router/index.js:4-31` |
| Несогласованный trailing slash: 69 путей со слэшем, 46 без | `backend` | `api/cart.py`, `api/admin.py:107,120` |
| Нет HPA и NetworkPolicy; нет security headers в nginx (только `Cache-Control`) | `infra` | `frontend/nginx.conf:40` |
| Глобальная миграция форм на `.field`/`.field__input` (§19): классы созданы в PR #252, применены только в Cart; 11 компонентов дублируют scoped-стили (Login, Register, ProfileRecipients, Admin и др.) | `frontend` | `assets/base.css:149-173`, spec 3-C D-02/Option B |
| PDP-фичи из §20 без данных/логики: Buy now, Delivery/Warranty-секции, Related products, Recently viewed (отложены из этапа 3-B, D-06) | `frontend` | `.agent/runs/design-catalog-pdp-pr209/spec.md` D-06 |

---

## Ждут решения владельца

В коде по нулям — прежде чем заводить, надо решить, нужны ли они вообще.

| Что | Проверено |
|---|---|
| Self-service onboarding продавцов (backend + UI) | `grep onboarding` → 0 |
| Product variants (size/color/SKU) — строим сами или приходят из 1С? | `grep -i variant` по моделям → 0 |
| Sub-orders + комиссии и выплаты — многопоставщиковая модель в планах? | в `app/` → 0 |
| Промокоды и купоны | `grep coupon\|promo` → 0 |
| Возвраты как пользовательский сценарий | `refund` есть в `yookassa_service.py:255`, эндпоинта нет |
| Pinia вместо композаблов; модерация; refresh tokens в HttpOnly | `pinia` нет в `package.json`; `grep -i moderat` → 0; `refresh_token` в `api/auth.py` → 0 |

---

## Блокеры

Живут в `docs/blockers.md`. На 2026-09-03 из активных:

- **BLK-009** (СДЭК `calculate` → 502) — факт-чек 2026-09-20 (API + браузер): воспроизводится
  только на неточном адресе до двери без дома, виджет сам просит уточнить и восстанавливается;
  UI не заблокирован. Переформулирован в P3: остаток — маппинг клиентского 400 СДЭК в 502.
- **BLK-010** (вебхук ЮKassa не доходит) — код готов целиком, открытая часть только одна:
  прописать URL в личном кабинете ЮKassa. Это шаг владельца, а не разработки.
- **BLK-013** (E2E тестовых карт) — **фактически обойдён**: PR #95 закрыт без мержа, а в `main`
  живут `checkout-failed-cards.spec.js` и `yookassa-test-cards.js` через debug-эндпоинт.
- ⚠️ **BLK-012 числится решённым неверно.** Запись говорит о миграции на `ghcr.io`, но миграция
  откачена — `42a2703 revert(ci): вернуть Harbor registry вместо GHCR` (PR #123, 25.07). CI
  по-прежнему на `harbor.kubeadm.ru`, `grep ghcr` по дереву даёт ноль.

---

## Закрыто по сверке 2026-09-03

Числились открытыми, оказались сделанными или отменёнными. Доказательства — в git и коде.

| Было | Как на самом деле |
|---|---|
| #10 `Product.price` → `Numeric(10,2)` | миграция `8965b510122d`; цена вынесена в `product_prices` |
| #16 unit-тесты `useCart` | `frontend/src/__tests__/useCart.spec.js` |
| #17 distributed rate limiting (Redis) | `utils/rate_limiter.py:13-15` (**но ключ неверный** → #220) |
| #19 CronJob вместо Celery Beat | `cronjob-cdek-create-orders.yaml`, `cronjob-cdek-sync-statuses.yaml` |
| #26 email/уведомления в `job_worker` | `workers/job_worker.py:131,226` |
| #27 `state` nonce в OAuth | `services/oauth_state.py` — сделано с запасом, ещё и PKCE |
| #41/#15 расширенные данные получателя | `models/recipient.py`, миграция `a14b9dfe3bd1`, `ProfileRecipients.vue` |
| #31 интеграция СДЭК | `cdek_client.py`, `cdek_service.py`, `api/cdek.py`, 2 CronJob, виджет |
| #34 FTS на PostgreSQL `tsvector` | отменено реализацией Meilisearch (`search_query.py`, `search_indexing.py`) |
| #1 интеграция ЮKassa | все 8 подзадач `done`, статус родителя не обновляли |
| Issue #5 «Кнопка Отменить заказ» | реализовано целиком с возвратом денег — **issue закрыт 03.09** |
| Icebox «Elasticsearch (миграция с tsvector)» | базы `tsvector` нет и не будет; переформулировать или снять |

---

## Завершённые спринты

Историческая запись. Sprint 1 (2026-06-29 — 2026-07-12): реальные платежи, гостевая корзина,
OAuth production-ready, вынос hardcoded secrets. Подробности каждой задачи — в `docs/journal/session-log.md`
и `docs/journal/session-log-archive.md`, решения — в `docs/decisions/log.md`.
