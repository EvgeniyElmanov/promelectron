> История старше хвоста — в SESSION_LOG.archive.md

### 2026-08-29 | fix (backend-dev) | fix-order-emails — EXECUTE DONE (issue #199), готово к ревью
  - **Финал (оркестратор):** коммит `6742046` + S001-fix `5b8c944`. Review it.1: code APPROVED, security FIXES_NEEDED (S001 MEDIUM — HTML-инъекция трека из CDEK в письмо; исправлено html.escape/quote, VERIFIED в it.2) → **APPROVED**. Полный прогон после S001: 625 passed/2 skipped ✅ (два обрыва Ошибка 137 — host OOM, PyCharm ~1.5GB; не код). Открыт **PR #200** (https://github.com/AutonomaCo/promelectron/pull/200), issue #199 → In review. S002 (LOW, пре-существующий escaping product_name/shipping_address) — follow-up. **Смержен в main** (merge `232fc35`, одобрено пользователем), issue #199 → Done. Deploy-run 33246172467 полностью зелёный (deploy-test + e2e ✅) — фикс на test-окружении.
  Запрос: дубль письма «Заказ оформлен» на цикле create+pay + нет трека в shipped-письме. Worktree `.worktrees/fix-order-emails`, ветка `bugfix/fix-order-emails`. PLAN.md одобрен без изменений.
  - Root cause: (1) `EmailService.send_order_confirmation` вызывался и при создании заказа (`order_service.py:256` auth / `:392` guest), и при успешной оплате (`payment_service.py:309`) с одним шаблоном «оформлен» — два одинаковых письма; guest-путь дублировался через тот же блок payment-ветки (welcome-письмо — не дубль, не тронуто). (2) `send_order_status_update` (`email_service.py:254`) не принимал трек, хотя `cdek_order.cdek_number`/`order.tracking_number` уже сохранены в `apply_cdek_status` (`cdek_service.py:513-526`).
  - Фикс: новый шаблон `EmailService.send_order_paid` («Заказ оплачен», соответствует нотификации `order_paid`); `payment_service.py:309` переведён на него. `send_order_status_update` получил опциональные `tracking_number`/`tracking_url` (блок рендерится только при наличии трека); `apply_cdek_status` прокидывает их (`order.tracking_number or cdek_order.tracking_number or cdek_order.cdek_number` + `build_tracking_url`).
  - Регрессионные тесты: `test_send_order_paid_creates_job`, `test_send_order_status_update_with_tracking` (+ `without_tracking`), `test_payment_success_sends_single_confirmation`, `test_apply_cdek_status_shipped_email_includes_tracking`. Подтверждено stash'ем `backend/src`: все 4 ключевых теста падают до фикса, после — зелёные. Обновлены моки `test_payments.py` (patch `send_order_confirmation` → `send_order_paid` в payment-ветке).
  - Проверки: полный `make test-backend` — **623 passed, 2 skipped, 0 failed** ✅; `make lint-backend` — чисто ✅.
  - Отклонения от PLAN.md: нет. Блокеры: нет. Не запушено. Следующий шаг: code-reviewer → PR.

### 2026-08-29 | fix (backend-dev) | fix-cdek-order-number-collision — EXECUTE DONE (issue #195), готово к ревью
  - **Финал (оркестратор):** code review APPROVED (findings нет), security APPROVED (S-001 low — пре-существующий log forging, follow-up). Открыт **PR #197**, **смержен в main** (merge `75f5850`, одобрено пользователем), issue #195 → Done. Урок записан в LESSONS_LEARNED (reseed БД + внешний стенд = коллизия идентификаторов). После деплоя: развязать INVALID-заказ #10 на test (удалить на стенде + resync).
  - **Deploy + верификация (2026-08-29):** run 33236209104 полностью зелёный (deploy-test + e2e ✅). Фикс подтверждён на живом test: заказ seed-прогона ушёл в CDEK с номером `PM-8-e84f00` — коллизии `..._has_already_had_integration` больше нет. Заказ #10 пользователя был затёрт reseed'ом (`seed-test-catalog` в CI) до resync; INVALID-сидовские заказы теперь падают только по `appropriate_pickup_point_not_found` (фейковый TEST_PVZ_1 в E2E-данных — ожидаемо). Пользователю: оформить заказ заново.
  Запрос: `CdekService.create_cdek_order` шлёт в CDEK `"number": str(order.id)`; после reseed БД на test id коллидируют с живыми заказами на стенде → `error_validate_im_dep_number_has_already_had_integration`, заказ #10 INVALID, трек не присваивается. Worktree `.worktrees/fix-cdek-order-number-collision`, ветка `bugfix/fix-cdek-order-number-collision`, коммит `6106ddf`. PLAN.md одобрен без изменений.
  - Фикс (`cdek_service.py`): `number` → `f"PM-{order.id}-{uuid.uuid4().hex[:6]}"` (+`import uuid`, комментарий); webhook-fallback по `attributes.number` научился извлекать id из формата `PM-{id}-{suffix}` (ветка рядом с legacy `order-{id}`; голый int и uuid-основной путь сохранены). Retry на коллизию не добавлялся (spec Decision, KISS).
  - Регрессионные тесты (`test_cdek.py`, хелпер `_capture_create_payload`): `test_create_cdek_order_sends_unique_pm_number`, `test_create_cdek_order_number_unique_across_calls`, `test_handle_order_status_webhook_finds_by_pm_number` — до фикса все 3 падают (проверено stash'ем сервиса: 3 failed), после — зелёные.
  - Проверки: полный `make test-backend` — **618 passed, 2 skipped, 0 failed** ✅ (первый прогон: 2 новых теста упали — в хелпере не был задан `user.phone`, исправлено, это тестовый setup, не фикс); `make lint-backend` — чисто ✅.
  - Отклонения от PLAN.md: нет. Блокеры: нет. Не запушено. Следующий шаг: code-reviewer → PR. Out of scope: ручная развязка INVALID-заказа #10 на test после деплоя (удалить на стенде + resync).

### 2026-08-28 | fix (оркестратор, e2e) | e2e-cart-select-race — PR #193 открыт
  После мержа #192 deploy-test прошёл (maxSurge-фикс работает), E2E: 117 passed / 1 failed / 1 flaky. favorites.spec.js зелёный (фикс #189 подтверждён на живом окружении), flaky checkout Mir no-3DS — известный BLK-013.
  Failed: cart-select.spec.js:240 — `expect(apiStatus).toBe(400)`, получено 200 (3/3 retries). Root cause — гонка: `toggleSelectAll` (Cart.vue) обновляет чекбоксы оптимистично, тест слал прямой `fetch /orders/create/`, обгонявший `POST /cart/deselect-all/` → бэкенд видел выбранные товары. К #189/#191/#192 отношения не имеет — латентная гонка на смещении таймингов после передеплоя.
  Fix (worktree `.worktrees/e2e-cart-select-race`, ветка `bugfix/e2e-cart-select-race`, коммит `0659cc6`): клики select-all/deselect-all обёрнуты в `waitForResponse` (паттерн уже использован в этом же spec). Проверки: `playwright --list` парсится; полный прогон — в CI после мержа.
  PR #193: https://github.com/AutonomaCo/promelectron/pull/193 — MERGED по одобрению пользователя; run 33185785733 полностью зелёный (build/deploy-test/migrate-check/seed/smoke/e2e ✅), cart-select детерминированно проходит.

### 2026-08-28 | fix (оркестратор, infra) | test-deploy-maxsurge — PR #192 открыт
  Симптом: deploy-test падает дважды после мержа PR #189 — `helm upgrade --wait` timeout (run 33173289692).
  Root cause: shared-кластер на пределе CPU requests; rolling update с `maxSurge: 1` не может разместить surge-поды api/job-worker (`3 Insufficient cpu`, Pending → ProgressDeadlineExceeded). Дефицит предшествовал мерджу (FailedScheduling с 12:30 UTC), к коду фикса отношения не имеет. Кластер/чужие namespace'ы не трогаем (решение пользователя).
  Fix (worktree `.worktrees/test-deploy-maxsurge`, ветка `bugfix/test-deploy-maxsurge`, коммит `3530a36`): strategy параметризована через `dig` (дефолт 1/0, prod без изменений; `default` в Go templates считает 0 пустым — поэтому dig), `stage/test/values.yaml` → maxSurge 0/maxUnavailable 1 для api/frontend/job-worker. Проверки: helm template test → 0/1, prod → 1/0, helm lint чисто.
  PR #192: https://github.com/AutonomaCo/promelectron/pull/192 — MERGED по одобрению пользователя; deploy-test в run 33182200993 зелёный (фикс подтверждён).

### 2026-08-28 | fix (backend-dev) | fix-cdek-tracking-number — EXECUTE DONE (issue #190), готово к ревью
  Запрос: после отправки товара трек-номер от CDEK не приходит. Scope A (согласован): обработка INVALID CDEK-заказов. Worktree `.worktrees/fix-cdek-tracking-number`, ветка `bugfix/fix-cdek-tracking-number`, коммит `7036c40`. PLAN.md одобрен без изменений.
  - Root cause: CDEK-заказ в статусе INVALID (например, несуществующий ПВЗ) никогда не получает `cdek_number`; INVALID не входил в `CDEK_TERMINAL_STATUSES` → `handle_cdek_sync_status` (`job_worker.py`) перепланировал sync-джоб бесконечно, ошибка нигде не была видна.
  - Фикс: (1) явная ветка INVALID в `handle_cdek_sync_status` — `sync_failed=True`, `sync_attempts+=1`, запись в `job.processing_log`, без reschedule; (2) cron `cron_cdek_sync_statuses` не подбирает заказы с `sync_failed=True`; (3) `INVALID` добавлен в `CDEK_TERMINAL_STATUSES` во всех 4 местах (config.py, .env.example, docker-compose.yml, helm values.yaml). Schema/frontend не менялись — `CdekOrderOut.sync_failed` уже отдаётся в API.
  - Регрессионные тесты (`test_cdek.py`): `test_handle_cdek_sync_status_invalid_marks_failed_and_stops`, `test_cron_sync_statuses_skips_sync_failed` — до фикса падают (sync_failed False / created 2), после — зелёные.
  - Проверки: полный `make test-backend` — **615 passed, 2 skipped, 0 failed** ✅ (первый прогон дал 359 errors из-за гонки template-БД с убитым по таймауту параллельным прогоном — известная проблема Single Test Run Rule, перезапуск чистый); `make lint-backend` — чисто ✅.
  - Отклонения от PLAN.md: нет. Блокеры: нет. Не запушено. Следующий шаг: code-reviewer → PR.
  - **Финал (оркестратор):** review iteration 1 — FIXES_NEEDED (1 minor F-001: корневой `.env.example` без INVALID, исправлен коммитом `32ff174`); iteration 2 — **APPROVED** (F-001 VERIFIED), security review — APPROVED. Открыт **PR #191**, **смержен в main** (merge `dfc1c83`, одобрено пользователем), issue #190 → Done.
  - **Deploy-эпилог (2026-08-29):** deploy-test после мержа #191 упал по `helm upgrade --wait` timeout — тот же CPU-дефицит кластера + maxSurge:1, что уронил deploy #189 (не код фикса). Разблокирован мержом PR #192 (maxSurge 0 для test). Финальный run 33185785733 (merge #193, tip main) полностью зелёный: build/deploy-test/migrate-check/seed/smoke/e2e ✅. Фикс подтверждён на живом test: в поде api `cdek_terminal_statuses` содержит INVALID, поды api/frontend/job-worker Running. Metrics: `.agent/runs/fix-cdek-tracking-number/metrics.json`, estimated tokens 3251. Урок записан в LESSONS_LEARNED (конфиг-ловушка 5 копий CDEK_TERMINAL_STATUSES). Out of scope: prod-конфиг CDEK (edu URL, SDEK_* vs CDEK_* в prod SOPS), регистрация webhook-подписки, трек в email. 2026-08-29: пользователь подтвердил — prod-ключей CDEK пока нет → заведён **BLK-014** (BLOCKERS.md + PROJECT_CONTEXT.md) с чек-листом на момент получения ключей.

### 2026-08-28 | оркестратор | context-sync --quick + аудит агентского пайплайна (P0/P1 исправления)
  По запросу пользователя: проверены новости Kimi K3 (релиз 16.07.2026, open weights 27.07, интеграция в GitHub Copilot 06.08) и проведён полный аудит пайплайна (.kimi-code/ + scripts/). Исправлено (без коммитов):
  - `implement-pipeline.py`: `--branch-prefix {feature,bugfix}` в setup/create-worktree/cleanup — fix-пайплайн больше не плодит сирот; `fix/SKILL.md` вызывает с `--branch-prefix bugfix`.
  - Trace-события (`task_created`/`review_verdict`/`qa_done`/`pr_opened`) добавлены в `fix`, `review`, `qa-gate`, `ship` SKILL.md — раньше trace писали только implement/deploy, `pr_opened` не писался никогда.
  - Ротация SESSION_LOG: 3836 → 290 строк (горячий хвост сверху, файл в обратном хронопорядке), архив в SESSION_LOG.archive.md (3563 строки); правило «читать только tail ~200» в agent-commons.md и AGENTS.md.
  - e2e-tester: flaky email pattern → `test_${Date.now()}_w${workerIndex}@example.com` (LESSONS_LEARNED §3).
  - Pinia (нет в проекте) вычищена из frontend-dev/promelectron/dispatcher/prompt-format → composables; prompt-format: пути `frontend/tests/e2e/` → `frontend/e2e/`, `src/services/` → `src/api/`.
  Context-sync: PROJECT_CONTEXT.md приведён к реальности (frontmatter 2026-07-02 → 2026-08-28, спринты завершены → issue-driven, +10 новых «работает», тесты 613/374/E2E 116+4skip). BLOCKERS.md: BLK-009/010 эскалированы (67 дней, просрочены), BLK-013 просрочен — все три требуют действий пользователя (CDEK прокси, webhook URL в ЛК YooKassa, реальные ключи). BACKLOG.md: Sprint 1 помечен завершённым. Тесты не прогонялись (--quick), взяты последние известные из лога. Остаток аудита: P1 (метрика review_iterations, дедуп блоков API-ограничений), P2 (cron/hooks, формат task.md), стратегическое (сериализация тестов на единой Docker-PG, лимит 100 items на board).

### 2026-08-28 | fix (frontend-dev, оркестратор) | favorites-remove-broken-and-heart-fill-0828 — MERGED (issue #188, PR #189)
  Запрос: на `/favorites` товары не удаляются (POST add вместо DELETE → 400), карточка не исчезает из списка, сердечко не закрашивается. Issue #188.
  Что сделано (worktree `.worktrees/favorites-remove-broken-and-heart-fill-0828`, ветка `bugfix/favorites-remove-broken-and-heart-fill-0828`, PLAN.md auto-approved):
  - Root cause: `Favorites.vue` передавал в `ProductCard` `item.product` (ProductOut без `is_favorite`) → локальный `isFavorite` всегда false → клик шёл в `POST /favorites/add/{id}` → 400 «Product already in favorites»; плюс `ProductCard` не уведомлял родителя об удалении; SVG сердечек с жёстким `fill="none"`.
  - `frontend/src/views/Favorites.vue`: `:product="{ ...item.product, is_favorite: true }"` + обработчик `@removed="removeFavorite"` (фильтр списка по `product.id`).
  - `frontend/src/components/ProductCard.vue`: `defineEmits(['removed'])`, emit после успешного DELETE; SVG `:fill="isFavorite ? 'currentColor' : 'none'"`; CSS transition fill + keyframes `heart-pop` (1→1.25→1).
  - `frontend/src/views/ProductDetail.vue`: тот же fill и анимация для `pdp-favorite-button`.
  - Регрессионные тесты: `ProductCard.spec.js` (+3: DELETE+emit removed при is_favorite, POST без removed при неактивном, fill currentColor/none), `Favorites.spec.js` (+1: карточка исчезает из DOM после события removed), `ProductDetail.spec.js` (+2: fill при активном/неактивном).
  Проверки: `npx vitest run` в worktree — 380/380 passed (37 файлов) ✅; `npx eslint src/` и `npx oxlint src/` — 0 warnings/errors ✅ (make-таргеты требуют Docker, прогон локальный через symlink node_modules). Коммитов нет — изменения в рабочем дереве worktree.
  Блокеры: нет. Следующий шаг: code review по /skill:fix Step 7.
  Финал: review APPROVED без findings; коммит `76c947e`, PR #189 (https://github.com/AutonomaCo/promelectron/pull/189) смержен в main по одобрению пользователя (merge 2026-08-28), issue #188 → Done. Knowledge capture: known-pitfalls.md №13 (фронтенд читает поле, которого нет в response schema). Review iterations: 1. Estimated tokens: ~3.3k.

### 2026-08-27 | оркестратор (+ backend-dev/frontend-dev/reviewers на ветках) | закрытие остатка бэклога: #160–162, #176, инфра-долг #179
  Продолжение ревизии 2026-08-26: пользователь подтвердил «делай» по остатку бэклога — три параллельные ветки, все смержены в main за сессию.
  - **PR #180** (`feature/backend-fixes-160-162`, merge `ca02529`) — backend-пакет: #160 (serve_upload MinIO-ветка ловит шире FileNotFoundError + re-raise HTTPException, finding S001), #161 (test_seed_catalog_script в Docker), #162 (X-1C-Checksum на /onec/intake/). Review APPROVED (3 ревьюера), 613 passed, lint чист. Issues → Done.
  - **PR #181** (`feature/out-of-stock-badge-176`, merge `2fb02d5`) — #176 бейдж «Нет в наличии» в ProductCard при stock=0 (остаток #163). Review APPROVED, 374/374 vitest, lint чист. Issue → Done.
  - **PR #182** (`feature/infra-test-e2e-concurrency`, merge `3f38da3`) — инфра-долг 11–13 (issue #179): (1) `make test-e2e` починен — убран `\&\&`, SEED_SECRET резолвится из `.env`/`../../.env` с fallback на dev-placeholder `.env.example` (корневой `.env` его НЕ содержит — третья причина, найдена в прогоне), `frontend-test` исключён из `up -d` (его `npm ci` вайпит примонтированный node_modules и гоняется с dev-server/playwright: `vite: not found` → EACCES root-owned); проверка — 116 passed/4 skipped. (2) `deploy.yml` — concurrency-группа `deploy-<ref>` с cancel-in-progress: серия мержей #180–182 её сразу проверила — два ранних deploy-run отменены, итоговый (tip main) в работе. (3) `implement-pipeline.py create-worktree` — `_prepare_frontend_deps` (host npm ci → контейнерный npm install → chown 1000:1000), флаги `--skip-frontend-prep`/`--prepare-frontend`; SKILL.md implement обновлён. Урок 2026-08-27 в LESSONS_LEARNED.
  - **Продуктовые решения:** GuestCheckout (#111) — оставить выключенным (410 Gone), точка. `/search/recommendations/` — **похоронено решением пользователя 2026-08-27**: фича «пустой поиск-оверлей» (Часто ищут / Популярные категории / Вам может понравиться в SearchBar); backend endpoint никогда не существовал, в #171/#173 фронт переведён на `/products/` с сохранением формата Recommendations — так и остаётся, endpoint не реализуем.
  - **Остаток tech-debt:** привести `alembic check` в зелёное состояние (pre-existing drift: `categories.is_active`, `cdek_orders`, `ix_email_verification_tokens_user_id`) — заведён issue #183 (Backlog).

### 2026-08-26 | implement (backend-dev + frontend-dev + reviewers + qa + e2e-tester, оркестратор) | restore-cart-select-items-177 — восстановление выбора товаров в корзине (issue #177, PR #178)
  Полный цикл /skill:implement в worktree `.worktrees/restore-cart-select-items-177` (ветка `feature/restore-cart-select-items-177`):
  - **Spec:** восстановление по `fe6f0f9` как референс без cherry-pick (main ушёл: product_prices, Recipient v1, #111). Ключевые решения: D-01 drift чинится возвратом колонки в модель БЕЗ новой миграции (миграция `9614c59dd5a3` в цепочке); D-02 guest checkout out of scope (410 Gone); D-03 default recipient/address не восстанавливаем (Recipient v1 + CDEK-виджет); D-04 пустой выбор → 400 до side effects. Одобрена пользователем.
  - **Backend (`1c6889b`):** `CartItem.selected` в модель; `CartItemOut += selected`, `CartItemSelectIn`, `CartItemCreate += selected=True`; `select_cart_item` (ownership 404) + `set_all_selected`; endpoints `PATCH /cart/select/{id}/`, `POST /cart/select-all/`, `POST /cart/deselect-all/` (trailing slash); `create_order` — только выбранные, невыбранные остаются в корзине; merge переносит `selected`. +10 тестов.
  - **Frontend (`e5abb30`, фиксы `34a3dbd`):** чекбоксы `cart-item-select` + select-all (indeterminate) в `Cart.vue`, итоги/sticky/CDEK по выбранным, disabled при 0, auth — оптимистичное обновление с откатом, guest — localStorage-хелперы; merge payload с `selected`. +14 тестов.
  - **Review (2 итерации, APPROVED):** backend/frontend/security параллельно. Ит.1 — F001 (API Inventory — закрыт оркестратором, `ac3ab9a`), F002 (денежный риск: `selectedDelivery` не инвалидировался при смене состава → watch на `selectionSignature` `id:quantity` + `supplierId`; решение H-001 пользователя — чинить сразу), F003 (a11y: aria-label + hit area ~44px). Ит.2 — все VERIFIED. Security: 0 CRITICAL/HIGH/MEDIUM.
  - **QA:** 607 passed/2 skipped backend, 371/371 frontend, lint чист; alembic на чистой БД `qa177_tmp`: downgrade/upgrade чисто, diff по `cart_items.selected` отсутствует; pre-existing drift (`categories.is_active`, `cdek_orders` и др.) — known, вынесен как follow-up (сделать `alembic check` зелёным).
  - **E2E:** новая `frontend/e2e/cart-select.spec.js` (`ac3adbb`, 2/2 PASSED): guest→login→merge сохраняет выбор; заказ только из выбранных + 400 при пустом. Regression: auth+catalog — 6 passed/4 skipped (facet-скипы by design). Локально ручной обход `make test-e2e` из LESSONS_LEARNED.
  - **Knowledge capture:** LESSONS_LEARNED +1 (коммит из устаревшего working tree молча откатывает фичу — второй случай класса после `7a89c8d`; профилактика: ревизия «закрыто ≠ реализовано», зелёный `alembic check`).
  - Review iterations: 2. QA iterations: 1. Estimated tokens: ~12k (check-context).
  - **PR #178 открыт**, issue #177 → In review. **Смержено 2026-08-26** (merge `1569056`), issue #177 closed → Done. CI деплоит main на test-окружение, E2E-suite — в CI.

### 2026-08-26 | оркестратор | ревизия закрытых spec-issue + синк трекера
  Полная ревизия «закрытых как Done» spec-issue (7 шт., swarm из explore-субагентов, read-only, по коду/тестам/git-истории):
  - **#96, #104, #107, #112, #134, #137/#138 — РЕАЛИЗОВАНО** (PR #97, #106, #108, #113, #135+#136, #140 соответственно; acceptance criteria подтверждены кодом и тестами в main). Guest E2E-сценарий из #96 позже осознанно удалён вместе с soft shutdown guest checkout (#111).
  - **#61 (cart-select-items-for-payment) — ЧАСТИЧНО: фича случайно откачена.** Реализована в PR #62 (`fe6f0f9`), на следующий день молча откатана коммитом `41a5043` (собран из устаревшего working tree). В main: backend фичи нет вообще (модель без `selected`, но миграция `9614c59dd5a3` в цепочке — drift схема/модель; нет `/cart/select/*`; `OrderService.create_order` берёт все товары), frontend без чекбоксов, `api/cart.js:3-4` зовёт несуществующий endpoint. Восстановимо целиком из `fe6f0f9` (+`a7215a8`, `d076f8d`).
  - **Заведён issue #177** «restore: cart-select-items-for-payment» → борд Promelectron, статус Backlog. Первый кандидат на /skill:implement.
  - **Синк `.agent/BACKLOG.md`:** строки #96/#104/#107/#112/#134/#137 `backlog → done` (с номерами PR); добавлены отсутствовавшие открытые backlog-issue #160 (MinIO serve_upload 500), #161 (test_seed_catalog_script в Docker), #162 (X-1C-Checksum) и #177.
  - **Открытое наблюдение:** `auth.spec.js` guest-cart-merge однажды дал flaky retry в CI (run 32924960820) — понаблюдать. Follow-ups вне scope спек: prod-reindex Meilisearch для `images`, удаление shim `normalizeSuggestions`, пункты 11–13 инфра-долга (Makefile `\&\`, concurrency в deploy.yml, подготовка worktree) — по-прежнему актуальны.
  - **Продуктовые вопросы на пользователе:** судьба GuestCheckout (#111, возвращать?) и `/search/recommendations/` (endpoint не реализован, фронт-вызов убран в #173).

### 2026-08-25 | frontend-dev | mobile-medium-fixes — пачка medium-фиксов мобильной версии (issue #171)
  Реализовано по spec.md в worktree `.worktrees/mobile-medium-fixes` (ветка `bugfix/mobile-medium-fixes`), коммит `22fdd94`:
  - **F1 SearchBar:** видимый input в шапке мобильного оверлея (`data-testid="search-bar-mobile-input"`, тот же query-state, autofocus при открытии); `.search-bar__history-delete` — `opacity: 1` в media <768px (видна на touch).
  - **F2 useSearchSuggestions:** probe-флаг `search_api_unavailable` в sessionStorage после первого 404 на `/search/suggestions/` → дальше сразу fallback на `/products/` без 404-спама; несуществующий `/search/recommendations/` убран — прямой запрос `/products/` с сохранением формата Recommendations.
  - **F3 safe-area:** `viewport-fit=cover` в index.html; body `padding-bottom: calc(var(--bottom-nav-height) + env(safe-area-inset-bottom, 0px))`; та же формула (+env) в Cart, Checkout, OrderDetail, ProfileRecipients (+модалка), PaymentSuccess/Failed, GuestOrderSuccess.
  - **F4 Profile:** пункт «Уведомления» (router-link `/notifications`, `data-testid="profile-notifications-link"`) с бейджем unreadCount; guard `if (ws) return` в `useNotifications.connect()` против двойного WebSocket (Header + Profile).
  - **F5 iOS zoom:** глобально в base.css `@media (max-width: 767px) { input, select, textarea { font-size: 16px !important; } }` — `!important` нужен, т.к. формы задают 15px scoped-классами (отклонение от литеральной формулировки spec, зафиксировано в отчёте).
  - Тесты: +5 кейсов SearchBar.spec.js (18 всего), +3 кейса useSearchSuggestions.spec.ts (+sessionStorage.clear в beforeEach). `npx vitest run` — **342 passed (37 файлов)** ✅, `npx oxlint src/` — 0 errors ✅.

### 2026-08-25 | оркестратор | перевод документации docs/ на drawio+SVG в едином тёмном стиле (заказ IT Александр)
  Все диаграммы документации перегенерированы в стиле референсов (C4, ортогональные стрелки, пунктирные boundary-фреймы, роли [Person], тёмная тема, подписи на русском):
  - **Тулчейн:** drawio desktop 31.3.2 распакован локально в `~/tools/drawio-dist` (без sudo), обёртка `~/tools/drawio`; headless-рендер `~/tools/drawio -x -f svg`. Генератор `scripts/docs/gen_diagrams.py` (~800 строк) эмитит `.drawio` XML для всех 8 диаграмм из декларативных описаний, флаги `--render`, `--only`.
  - **Созданы:** `docs/architecture/01-c4-system-context`, `docs/architecture/02-c4-containers` (+README), 5 sequence-флоу в `docs/flows/` (03-order-checkout, 04-cdek-delivery, 05-order-cancel-refund, 06-guest-cart-merge, 07-catalog-1c-sync), `docs/08-ai-agent-pipeline` — каждая `.drawio`+`.svg`, все просмотрены глазами через проверочные PNG. Сквозная нумерация 01–08 задаёт порядок чтения (от общего к частному) в именах файлов, заголовках диаграмм и README.
  - **Удалены:** все `docs/flows/*.mmd`, `*.png` (включая устаревший `catalog-1c-sync-detailed.*`), `docs/ai-agent-pipeline.mmd`.
  - **Обновлены:** `docs/flows/README.md` (новая инструкция регенерации, абзацы «Критичное свойство», замечание про Meilisearch приведено к факту — реализован за feature flag), корневой `README.md` (mermaid-блок → SVG), `.kimi-code/skills/flow-implement/SKILL.md` (mermaid-шаблон встроен, т.к. читал удалённый .mmd).
  - **Уточнения по коду в ходе работы:** Meilisearch реализован (`search_service.py`, feature flag `catalog_search_meilisearch`); `/onec/intake/` существует (#118) — MinIO-вариант в catalog-1c-sync показан пунктирным opt-фреймом.
  - Компромисс: подписи sequence — отдельные text-ноды, стрелки на абсолютных точках (детерминированный рендер; в GUI не магнитятся — задокументировано в docstring генератора).

### 2026-08-24 | implement (backend-dev, оркестратор) | product-prices-table — цены в product_prices (issue #166, PR #168)
  Полный цикл /skill:implement в worktree `.worktrees/product-prices-table` (ветка `feature/product-prices-table`):
  - **Спека/план:** таблица `product_prices` (все виды цен 1С без потерь), `products.price` удалена; сайтовая цена — `column_property` с коррелированным подзапросом по `settings.onec_site_price_type` (env `ONEC_SITE_PRICE_TYPE`, default `"site"`); `onec_price_type_key` удалён из конфига/env/helm.
  - **Реализация (коммиты 26ea8d8, a7215a8):** модель `ProductPrice` + миграция `a1b2c3d4e5f6` (backfill `price>0 → 'site'`, обратимый downgrade); `services/price_service.py` (get_site_price/upsert_product_price, per-row staleness); webhook + intake (OData/CML) пишут все виды цен, активация товара только сайтовой ценой; заказ снапшотит сайтовую цену под FOR UPDATE (400 для бесценного); CDEK — `price_at_time`; схемы — `price` nullable, `ProductCreate.price gt=0`.
  - **Review (2 итерации, APPROVED):** ит.1 — 10 findings (HIGH: `changed` всегда True на reparse цен → ломал F007; MEDIUM: `price: null` ронял батч, staleness по разным часам → логирование skip); security-review отдельно — денежное ядро чистое. Все FIXED/VERIFIED.
  - **H-001 → вариант C:** backfill `'site'` ↔ `ONEC_SITE_PRICE_TYPE`; при подключении реальной 1С — data-миграция `price_type` отдельной задачей (зафиксировано в PROJECT_CONTEXT.md, ограничение №11).
  - **QA:** 589→**596 passed** (после merge main), lint чисто, миграция upgrade/downgrade/upgrade на чистой БД в Docker — OK. E2E 114 passed/4 skipped.
  - **Merge с main перед ship:** конфликт в `product_service.py` (импорты) разрешён вручную; PR #167 (PDP attributes) смержен, семантика detail (price + attributes) проверена.
  - **Инфра-приколы прогона:** свежий worktree — `npm ci` на хосте не ставит optional peer `picomatch` → vite падает; чинится прогоном `npm install` в playwright-контейнере (он ставит), но тот создаёт root-owned файлы → последующие `--user 1000:1000` run'ы падают молча; решается `chown -R 1000:1000` через `docker run node:20-slim`. `make test-e2e` локально по-прежнему сломан (`\&\&` + SEED_SECRET) — ручной обход из LESSONS_LEARNED (2026-08-24).
  - Review iterations: 2. Estimated tokens: ~9k (оркестратор, без субагентов).

### 2026-08-19 | implement (frontend-dev) | feat-out-of-stock-ui — индикация «Нет в наличии» (issue #163)
  Реализовано по PLAN.md в worktree `.worktrees/feat-out-of-stock-ui` (ветка `feature/feat-out-of-stock-ui`), коммит `687fabb`:
  - **`frontend/src/components/ProductCard.vue`**: бейдж «Нет в наличии» (`data-testid="out-of-stock-badge"`, поверх фото, `var(--color-danger)`) при `product.stock === 0`; кнопка `add-to-cart-button` — `:disabled="isLoading || isOutOfStock"` с текстом «Нет в наличии».
  - **`frontend/src/views/ProductDetail.vue`**: тот же бейдж (`data-testid="pdp-out-of-stock-badge"`, добавлен `position: relative` на `.product-detail__image`); кнопка `pdp-add-to-cart` — `:disabled="cartLoading || isOutOfStock"`.
  - Backend не тронут: `stock` подтверждён в обоих API (`ProductDetailOut` → `ProductBase.stock`, `SearchItemOut.stock`).
  - Тесты: +2 кейса в `ProductCard.spec.js`, +2 кейса в `ProductDetail.spec.js` (stock=0/stock>0). Нюанс: в ProductDetail waitFor на позитивный сигнал загрузки (`pdp-title`), т.к. `loading` стартует с `false` и кнопка рендерится до fetch.
  Проверки: `make test-frontend` — **332 passed (37 файлов)** ✅, `make lint-frontend` — 0 errors ✅. Отклонений от PLAN.md нет.
  Следующий шаг: code review, затем PR.

### 2026-08-19 | оркестратор | устранение wip-регрессии коммита 7a89c8d (PyCharm Local History)
  Коммит `7a89c8d` восстановил СТАРЫЕ версии файлов из Local History поверх новых закоммиченных — полный разбор всех 65 затронутых файлов:
  - **backend/src** (6 файлов): восстановлены из `7a89c8d^` — main.py (5 роутеров: cdek/onec/recipients/search/admin_search + serve_upload стриминг из MinIO вместо 307), api/admin.py (order detail, cancel с refund, onec full-sync), api/cdek.py (admin-guard resync, _ensure_sync_job), models/onec_sync.py (OnecIntakeLog — миграция 937fc6751168 существует), models/__init__.py, schemas/__init__.py.
  - **backend/tests** (6 файлов): conftest.py (make_settings factory из c56c168), test_auth (−1502 строки!), test_admin (−923), test_cdek, test_products, test_analytics.
  - **backend/docker-compose.yml**: откат Celery-версии (meilisearch, MINIO_INTAKE_BUCKET, ONEC_WEBHOOK_API_KEY возвращены).
  - **infra/helm**: Chart.yaml/values.yaml/api-deployment/migrate-job восстановлены (jobWorker, onecMock, meilisearch секции); `cronjob-sync-onec.yaml` удалён — ссылался на несуществующий `app.workers.sync_onec` (Celery-эпоха). `helm template` — OK.
  - **pipeline** (.kimi-code, Makefile, workflows, .env.example, README, AUDIT, .claude): трёхстороннее восстановление, сессионные правки блоков A/B сохранены; LESSONS_LEARNED (+168 строк), Makefile (test-onec-mock и др.), deploy.yml (seed-test-catalog job и др.).
  - **.agent/** (6 файлов): pre-wip база + пост-wip записи; SESSION_LOG вернул 330 строк истории (записи 31.07–14.08).
  - Оставлено намеренное: docs/flows/*, resume-hh.md, frontend/vite.dev.config.js. Удалено по решению пользователя: tmp_check_pull_result.py, tmp_check_supplier.py, frontend/e2e/debug-catalog.spec.js.
  - Дополнительно починен pre-existing фейл `test_seed_catalog_script.py` — pytest.skip при backend-only контейнере (scripts/ не смонтирован).
  Тесты: 57 failed + 32 errors (wip-состояние) → 4 failed → **568 passed, 2 skipped, 0 failed** после полного восстановления (финальный прогон).
  **Закоммичено в main** (одобрено пользователем): `1fd9763` fix: восстановление wip-регрессии (36 файлов), `db7afcd` feat(agent-pipeline): аудит + блоки A/B (36 файлов), `5a38662` test(backend): seed-catalog skip.

### 2026-08-19 | оркестратор | аудит агентского пайплайна — блок B (улучшения под Kimi K3)
  - **Унификация модели K2.7 → K3** во всём `.kimi-code/` (AGENTS.md, agent-commons, 15+ skills, config.example.toml, pre-edit-checklist); факты о контексте: 256K → 1M.
  - **Порог контекста** поднят 150K → 600K (~60% окна 1M): `implement-pipeline.py` `CONTEXT_THRESHOLD`, agent-commons, 5 workflow-skills, советы в ролевых skills; `max_context_size` в config.example.toml → 1048576.
  - **Параллельная разработка в implement**: Step 5 — по умолчанию backend-dev + frontend-dev параллельно (два Agent-вызова в одном сообщении, scope-границы backend//frontend/), новые флаги `--serial` (старое поведение) и `--qa` (обязательный `/skill:qa-gate` перед PR, Step 7.6). Соответствует обещаниям AGENTS.md.
  - **BUNDLE.md**: добавлены flow-fix/flow-implement/flow-review и rules/business.md, plan-maintainer дедуплицирован; реестр сверен с диском (24 skills, 10 rules).
  - **MCP-серверы** (mcp_atlassian.py, mcp_figma.py): dispatch в try/except (isError вместо краша), `arguments: null` нормализован, на JSON-RPC notifications не отвечаем, unknown method/tool → error -32601, порядок проверок в figma исправлен, docstring atlassian (cap 50).
  - **mcp.json**: `type: stdio` и `-y` для playwright/filesystem/memory/sequential-thinking (защита от зависания npx при старте).
  Верификация: audit-agents.sh зелёный; grep «K2.7|256K» по .kimi-code/ и scripts/ — чисто; ручные прогоны MCP-серверов — ок.
  Подтверждённая регрессия backend (НЕ исправлена, вне scope): wip-коммит 7a89c8d (PyCharm Local History) выкинул из main.py 5 роутеров — cdek, onec, recipients, search, admin_search. Ждёт решения пользователя.

### 2026-08-19 | оркестратор | аудит агентского пайплайна — блок A (починка критичных багов)
  Полный аудит пайплайна (24 skills, 10 rules, 6+ скриптов, конфиги) — 40+ находок. Исправлено (без коммитов):
  - **implement/SKILL.md**: миграция на `.agent/runs/<task-id>/` и `.worktrees/<task-id>/`; добавлены шаги 4.5 (GitHub Issue linking), 6 (review loop), 7.5 (e2e-tester), 8 (PR через /skill:ship), 8.5 (knowledge capture), 9 (final report) — закрыты битые ссылки из fix/qa-gate; убран EnterPlanMode из промпта архитектора; inline-преамбулы заменены ссылкой на agent-commons; команды тестов через корневой Makefile / `npm test`.
  - **Скрипты**: `agent_improve.py` — регэксп findings `[F-001]`→`[F001]` (основная функция была мертва); `implement-pipeline.py` — slugify для кириллицы (sha1-суффикс, устранены коллизии task-id), устойчивый create-worktree (точное сравнение путей, работа при существующей ветке); `block-dangerous-bash.py` — закрыты обходы (`rm -fr /`, `HEAD:main`, голый `git push`); `config.example.toml` — `git commit`/`git merge` → `decision = "ask"`.
  - **Доки/правила**: golden-path и PROJECT_CONTEXT приведены к реальным роутам (`/api/v1/register/`, `/api/v1/login/`, `POST /api/v1/products/`, без guest-cart/admin-products); правило trailing slash переформулировано (только новые endpoints); `deploy/SKILL.md` — починены вызовы `agent_state.py trace`; заголовок преамбулы в agent-commons унифицирован («Full subagent prompt block»).
  Верификация: `scripts/audit-agents.sh` — зелёный; ручные прогоны регэкспа/slugify/хука — ок.
  Отложено (блок B): унификация K2.7/K3 в skills и agent-commons, реестр BUNDLE.md (flow-*, business.md), харденинг MCP-серверов, параллельный backend+frontend через AgentSwarm.

### 2026-08-18 | implement (backend-dev) | fix-uploads-cache-onec — реализация по PLAN.md (issue #158)
  Три backend-фикса в worktree `.worktrees/fix-uploads-cache-onec` (ветка `feature/fix-uploads-cache-onec`), по коммиту на шаг:
  1. **Path traversal в `/uploads/`** (`2174f79`): `backend/src/app/main.py` (`serve_upload`) — отказ в `..`-сегментах пути (404) до обращения к storage в обоих режимах; local-ветка — `realpath` + prefix-проверка внутри `uploads` (закрывает и symlink-обход). Тесты: encoded `%2e%2e` в local и MinIO режимах (`backend/tests/test_serve_upload.py`).
  2. **Cache-Control** (`58e298f`): заголовок `Cache-Control: public, max-age=<UPLOADS_CACHE_MAX_AGE>` (default 86400) на 2xx-ответах MinIO- и local-веток. Новая настройка `uploads_cache_max_age` в `backend/src/app/core/config.py` + `UPLOADS_CACHE_MAX_AGE` в `backend/.env.example`.
  3. **Шум WARNING'ов onec_units** (`380f9c7`): `backend/src/app/services/onec_units.py` — заведомо текстовые значения («чёрный», «IP20») логируются на DEBUG; WARNING только для «почти числовых» промахов (начинаются с цифры). Парсинг не менялся (запятая, «мм2», диапазоны уже поддержаны); диапазоны остаются `value_text`, схема БД не тронута, миграций нет.
  Проверки: `make test-backend` — **571 passed, 1 failed, 1 skipped**; единственный фейл `test_seed_catalog_script.py::test_product_detail_url_has_no_trailing_slash` — **pre-existing** (воспроизводится на чистом main-репо без моих изменений: тест ищет `/scripts/ci/seed_test_catalog.sh`, которого нет в контейнере; к диффу отношения не имеет). `make lint-backend` — чисто ✅. Дополнительно `ruff check src/ tests/`: 1 pre-existing F401 в `backend/tests/test_email.py:6` (не мой файл, не трогал).
  Отклонения от PLAN.md: нет по коду; известные pre-existing фейлы зафиксированы выше.
  Следующий шаг: code review (+ security-reviewer), затем PR.

### 2026-08-14 | fix | e2e-search-filter-wait — PR #157 MERGED
  Root cause: после #156 (enqueue SEARCH_INDEX_PRODUCTS после upload/delete фото) тест `frontend/e2e/search-filter.spec.js:48` «category filter shows only products from selected category» стал flaky в CI (run 31799254592): фиксированный `waitForTimeout(400)` не успевает за refetch под нагрузкой ~40 фоновых partial-reindex jobs в Meili. Backend-фильтрация исправна (live `?category_id=1` → только розетки) — flaky по таймингу, не продуктовый баг.
  Фикс: `waitForTimeout(400/600)` в тестах «category filter…» и «search filters products by name» заменены на `expect(async () => {...}).toPass({ timeout: 15000 })` — паттерн соседних sort/price-тестов того же файла; условия внутри toPass — честные индикаторы (`count < allCount`, тексты карточек, +защита `count > 0` от транзиентного пустого списка). Один файл, 22+/19-.
  Проверка: прогон spec против test-стенда — все 4 теста зелёные (параллельные падения page.goto — локальный сетевой сбой, с --workers=1 проходят). Review: APPROVED без findings. Коммит `35188cb`, PR #157 влит в main (`6eedb82`). CI-прогон 31802278962 ожидается.

### 2026-08-03 | implement (backend-dev) | admin-order-modal-details — EXECUTE DONE, готово к ревью
  Issue #130. Worktree `.worktrees/admin-order-modal-details`, ветка `feature/admin-order-modal-details`, коммит `ed44c65` (только backend-файлы; frontend-dev работает параллельно в том же worktree).
  Что сделано (по PLAN.backend-dev.md):
  - `backend/src/app/schemas/order.py` — `AdminOrderItemOut` (product_name/sku/image_url/line_total), `AdminOrderBuyerOut` (name/email/phone), `AdminOrderDetailOut(OrderOut)` (+buyer, payment: PaymentOut, items_total, delivery_price). `OrderOut` и существующие endpoints не тронуты.
  - `backend/src/app/services/order_service.py` — `get_admin_order_detail()` (selectinload items→product, user, payment, recipient, cdek_order→status_history; 404) и `build_admin_order_detail()` (сборка ответа: fallback «Товар #id» при удалённом product, buyer из user или guest-полей, Decimal ROUND_HALF_UP, delivery_price = max(total − items_total, 0)).
  - `backend/src/app/api/admin.py` — `GET /admin/orders/{order_id}/` (trailing slash, `get_current_active_admin`).
  - `backend/tests/test_admin.py` — класс `TestAdminOrderDetail`: 9 тестов (happy path, 404, 403 user, 403 без токена, guest buyer, без payment, delivery_price > 0, clamp к 0, unit fallback удалённого товара).
  Тесты: полный `make test-backend` — 548 passed, 1 skipped ✅ (целевые 9/9 ✅). Lint: host ruff 0.15.13 (`ruff check src/ tests/`) по изменённым файлам чисто; `make lint-backend` падает с 455 ошибками на всём `src/` — pre-existing: в docker-образе ruff 0.16.1 (новее проектного), нетронутые файлы (products.py, cart_service.py) дают 20 ошибок. Не моя регрессия.
  Отклонения от плана: (1) сборку ответа вынес из handler'а в service (`build_admin_order_detail`) — правило «бизнес-логика в service»; (2) тест unauthorized ожидает 403 (проектный стандарт HTTPBearer), не 401; (3) тест удалённого товара — unit на `build_admin_order_detail` (FK не даёт удалить product через ORM).
  Блокеры: нет. Миграций нет (D-11). Не запушено.

### 2026-08-01 | fix (frontend-dev) | catalog-filter-panel-122 — LOW findings F001–F003 из ревью PR #135 FIXED
  Ветка `fix/catalog-search-low-findings` (worktree `.worktrees/catalog-filter-panel-122`), один коммит `62b8def`. Не запушено — push/PR делает оркестратор.
  - F001: stale-запрос с не-cancel ошибкой больше не пишет в `error.value`/`items`/`loading` — проверка `currentFetchId !== fetchId` в catch `useCatalogSearch.load`.
  - F002: числовые enum-значения восстанавливаются из URL — нормализация `String(value)` в `toggleFacetValue` (composable) и `isSelected` (FilterPanel.vue); сериализация query params не изменилась.
  - F003: 404 от `/search/` в обычном запросе сбрасывает module-scope кэш probe и ставит `searchAvailable=false` — UI откатывается на legacy `/products/` без показа ошибки (fallback-режим со следующего запроса).
  Регрессионные тесты: useCatalogSearch.spec.js +3 (F001 stale-ошибка, F002 число из URL, F003 mid-session 404), FilterPanel.spec.js +1 (числовой фасет отмечен по строке из URL). `make test-frontend` 307/307 ✅, `make lint-frontend` чисто.

### 2026-08-01 | implement (frontend-dev) | catalog-filter-panel-122 — EXECUTE DONE, готово к ревью
  Issue #122 (Фаза 6 эпика #117, `--frontend-only`). Worktree `.worktrees/catalog-filter-panel-122`, ветка `feature/catalog-filter-panel-122`.
  Что сделано (строго по PLAN.md, 5 шагов = 5 коммитов по чек-листу issue):
  - `frontend/src/api/search.js` — API-клиент search-endpoints по паттерну `api/cdek.js` (axios-инстанс `@/services/api`, trailing slash): `searchProducts` (`/search/`, `paramsSerializer: {indexes: null}` — повторяющиеся `attr.<code>` для FastAPI `multi_items()`), `getSearchSuggestions` (`/search/suggestions/`), `getFacetValues` (`/search/facet-values/`, зарезервирован для MVP+).
  - `frontend/src/composables/useCatalogSearch.js` — состояние фильтров + загрузка листинга: probe `/search/` (D-01, 404 → `searchAvailable=false`, кэш в module-scope, временные ошибки не кэшируются; тестовый хук `__resetSearchProbeForTests`), selected Map/Set (OR внутри группы через повторяющиеся `attr.<code>`), ranges `attrs_range.<code>=min:max`, price/sort/categoryId/q, URL query sync (`router.replace`, init из `route.query`), AbortController + fetchId + дебаунс 300 мс на `setQuery`, мгновенная загрузка на чекбоксах, `loadMore` по `page/pages`, `reset`. Без `console.error` (error-ref).
  - `frontend/src/components/FilterPanel.vue` — dumb-компонент (D-04): секции на нативном `<details>`, дерево категорий из фасетов `categories.lvl0/lvl1` (пути «Root > Child», имя→id через `categoryOptions` из `useCategories`, повторный клик снимает фильтр), чекбокс-группы с disjunctive counts, price и numeric-диапазоны с clamp по `stats {min,max}` + `unit`, полный набор `data-testid` (`filter-panel`, `filter-group-<code>`, `filter-value-<code>-<i>`, `filter-price-min/max`, `filter-apply`, `filter-reset`, `filter-range-*-<code>`).
  - `frontend/src/views/Products.vue` — ветвление `searchAvailable ? useCatalogSearch : legacy` (D-05), legacy-режим не переписан: probe последовательно до первой загрузки (без гонки), унифицированные computed `displayProducts/Total/Loading/HasMore`, FilterPanel слева на desktop (sticky, 260px) / сворачиваемый `<details>` на mobile, скрыты legacy-фильтр рейтинга и price-inputs, опция `rating_desc` исключена в search-режиме, общие сетка/skeletons/IntersectionObserver/«Показать ещё». Search items без `images` → letter-placeholder (известная деградация, backend follow-up).
  - `frontend/src/composables/useSearchSuggestions.ts` — D-06: `normalizeSuggestions` принимает обе формы (`{suggestions: [{type, id, name}]}` → products без price/image; старую — как есть), `MiniProduct.price` стал опциональным; SearchBar уже рендерил price/image под v-if — правок шаблона не потребовалось. `/search/recommendations/` в backend нет → существующий fallback на `/products/` покрывает, не менялось.
  - E2E `frontend/e2e/catalog.spec.js` — новый describe «Facet filters» с probe в `beforeAll` и `test.skip` при выключенном флаге (D-07): фильтрация + URL + disjunctive counts, восстановление по URL, price_min/max в URL, filter-reset; отдельный тест legacy-режима при 404 probe.
  Тесты: `make test-frontend` 303/303 зелёные (36 файлов; новые: useCatalogSearch 12, FilterPanel 11, useSearchSuggestions 4, Products +3, SearchBar +1); `make lint-frontend` чисто. E2E локально не прогонялись — окружение (localhost:5173) не поднято; сценарии скипаются/работают по probe на CI.
  Коммиты: d1ab0af (api+composable), 5980e81 (FilterPanel), ad5f7ee (Products.vue интеграция), e169f50 (suggestions D-06), ca99cd8 (unit+e2e coverage). Не запушено.
  Отклонения от PLAN.md: (1) SearchBar.vue не правился — price/image уже были под v-if, достаточно опционального `MiniProduct.price` + unit-теста; (2) маппинг suggestions тестируется в новом `useSearchSuggestions.spec.ts` (SearchBar.spec мокает composable целиком, маппинг там не проверить); (3) в worktree добавлен симлинк `frontend/node_modules` → основной checkout (gitignored, нужен для vitest).
  Блокеры: нет. Следующий шаг: code-reviewer → QA gate → PR. Известные ограничения: карточки без images и suggestions без price/image — принятые спекой деградации (follow-up issues на backend, зафиксированы в spec.md).

### 2026-07-31 | implement (backend-dev) | onec-attribute-loader-0731 — EXECUTE DONE, готово к ревью
  Issue #120 (Фаза 4 эпика #117). Worktree `.worktrees/onec-attribute-loader-0731`, ветка `feature/onec-attribute-loader-0731`.
  Что сделано (строго по PLAN.md, 4 шага = 4 коммита по чек-листу issue):
  - Модели `Attribute` (code unique, value_type enum number/enum/bool/string, unit NULL, is_filterable default false, sort, onec_id unique NULL) и `ProductAttributeValue` (typed-колонки value_number/value_text/value_bool, option_id без FK, unique(product_id, attribute_id)) в `backend/src/app/models/attribute.py` + миграция `194ccff2a461` (autogenerate-drift вычищен до двух create_table + индексов + drop enum в downgrade; upgrade/downgrade/upgrade проверены). Таблица `attribute_options` НЕ создана (out of scope).
  - `StorageService.download_raw(key, bucket=None) -> bytes` в Protocol + Local + Minio (FileNotFoundError на NoSuchKey/404 — единый контракт) — gap, выявленный оркестратором.
  - Парсер единиц `onec_units.py`: «10,0мм2» → (10.0, «мм²»), запятая → точка, диапазон «1,5-2,5» → текст (без warning), «2016/2025/2032» (единица без букв) → текст, нечисловое → текст + warning-лог; KNOWN_UNITS продублирована из анализатора Фазы 3 с комментарием о синхронизации.
  - Загрузчик `onec_intake_loader.py` + handler `ONEC_INTAKE_PROCESS` в `job_worker.py`: `download_raw` → детект формата (ZIP → CommerceML import/offers, OData JSON по odata.metadata) → upsert по `onec_id` (categories → products → attribute defs → values → prices → stock) по `docs/onec/FORMAT_MAP.md`, батчи 1000 с commit на батч; правило «активные» (IsFolder/ТипНоменклатуры≠Запас skip; DeletionMark=true → is_active=false); нормализация единиц на импорте (unit фиксируется в справочнике по первому числовому значению, D-10); цены только по `ONEC_PRICE_TYPE_KEY` + Актуальность; остатки суммой с клампом ≥ 0 (B-02); отчёт `onec_intake_log.status` = parsed/failed (+ error), счётчики в `processing_log` job'а; enqueue `SEARCH_INDEX_PRODUCTS` (handler — Фаза 5, падения Unknown job_type до неё приняты, задокументировано в коде и INTAKE_ENDPOINT.md).
  Тесты: 4 (модели) + 5 (download_raw) + 22 (onec_units) + 13 (загрузчик: идемпотентность, DeletionMark, «10,0мм2»→10.0/мм², цены/остатки, категории с parent, CommerceML ZIP, failed-кейсы, enqueue, handler) — все зелёные в Docker; ruff чисто.
  Коммиты: 8f9ef0f (models+migration), 8f9c29d (download_raw), 487311e (onec_units), da43df2 (loader+handler). Не запушено.
  Отклонения от PLAN.md: (1) новый env `ONEC_PRICE_TYPE_ID` не добавлялся — использован существующий `ONEC_PRICE_TYPE_KEY` (уже в Settings и onec_client); (2) KNOWN_UNITS не перенесена из scripts/ в src/, а продублирована — анализатор загружается через importlib и не может импортировать src.app.
  Блокеры: нет. Следующий шаг: code-reviewer → QA gate → PR. Известные ограничения: полный импорт ~100K на стенде не прогонялся (unit-тесты на фикстурах); enum-значения из `Catalog_ЗначенияСвойствОбъектов` резолвятся только в пределах одного пакета (in-run кэш), иначе GUID-строкой в value_text + warning.
  Дополнение (review итерация 1, вердикт FIXES_NEEDED → все 7 findings FIXED, коммит 1e915c8):
  - F001 (HIGH): `_load_cml_import`/`_load_cml_offers`/`_load_odata_stock` — батчи 1000 с commit на батч.
  - F002 (HIGH): защита от дублей sku — pre-check конфликта (in-run + БД), занятый sku не присваивается (warning + stats.errors), poison-файл исключён; тест есть.
  - F003 (MEDIUM): цены ≤ 0 игнорируются (B-01, warning + errors); новый товар создаётся `is_active=False` до первой валидной цены > 0; undelete — только при price > 0 (иначе reparse активировал бы товар без цены — поймано тестом F007). Тесты есть.
  - F004: лимит распаковки ZIP 400 МБ (zip-bomb → ValueError → failed); тест есть.
  - F005: сниффинг формата по первым 64 КБ, без полного json.loads.
  - F006: убраны избыточные PK-индексы (`index=True` на id + 2 create_index/drop_index в миграции 194ccff2a461).
  - F007: dirty-tracking (`cache.touched`) — SEARCH_INDEX_PRODUCTS ставится только на реально изменённые товары; reparse без изменений job не ставит (тест есть).
  Целевые тесты 49/49 ✅, ruff чисто, миграция upgrade/downgrade/upgrade перепроверена.
  Дополнение (review итерация 2, вердикт FIXES_NEEDED → F008/F009 FIXED, коммит e7c3de8):
  - F008 (HIGH): O(N²) скан кэша при проверке sku заменён индексом `cache.skus` (sku → onec_id, O(1)); все записи в кэш через `_register_product`; DB-select только при промахе; переназначение sku чистит старый ключ. Тесты: конфликт с БД-товаром, освобождение ключа при смене артикула.
  - F009 (MEDIUM): цена активирует только никогда не оценённый товар (`was_unpriced` фиксируется ДО присвоения цены — первая версия проверяла после, поймано регрессией); soft-deleted с ненулевой ценой ценой не реанимируется, восстановление — только товарным документом. Тест: DeletionMark-файл → prices-файл → is_active=False, цена обновлена.
  Целевые тесты 21/21 ✅, ruff чисто.

### 2026-07-30 | implement (backend-dev) | onec-format-analyzer-0730 — EXECUTE DONE (шаги 1–4), готово к ревью
  Issue #119 (Фаза 3 эпика #117). Worktree `.worktrees/onec-format-analyzer-0730`, ветка `feature/onec-format-analyzer-0730`.
  Что сделано (по PLAN.md, шаги 1–4; шаг 5 — после мёрджа PR #125):
  - `scripts/onec_format_analyzer.py` (~700 строк, stdlib + ленивый aiobotocore, без импорта приложения): сниффинг формата (ZIP magic → OData JSON → CommerceML → unknown), рекурсивный ZIP, реестр 9 сущностей + «прочие», классификация `#Collection(StandardODATA...)` и `/@Element`, статистика полей (fill rate, distinct, примеры), счётчики «всего/активных» по D-09, анализ характеристик (джойн по GUID, типы enum/number/string/bool, top-N, numeric-кандидаты «10,0мм2» → 10.0 мм²; второй проход по Owner_Key в property_values), перекрёстные ссылки по GUID (NULL GUID = NULL, D-08), сводка остатков (сумма, кламп ≥ 0, min построчный −4), CLI `--path` | `--minio` (D-07), отчёты markdown+JSON (D-05).
  - `backend/tests/test_onec_format_analyzer.py`: 32 self-contained теста (importlib, без БД/app-фикстур), incl. MinIO-итератор с моком aiobotocore и CLI end-to-end; module-level skip, когда scripts/ не смонтирован (docker test-backend монтирует только backend/).
  - Прогон по мартовским сэмплам: `docs/onec/reports/2026-07-30_march-samples.md` + `.json` — 17 JSON классифицированы (в task.md упоминалось «20 файлов» — фактически в каталоге 17 JSON + metadata.xml + логи/бинарники), 5 видов цен, отрицательный остаток −4, numeric-кандидаты мм²/шт.
  - `docs/onec/FORMAT_MAP.md` — 6 разделов, маппинг сверен с моделями `Product`/`Category`/`OnecChangeLog`; решение по видам цен (один базовый вид → products.price, GUID — env-конфиг Фазы 4); правило «активные» (D-08/D-09); CommerceML-диалект мока Фазы 7.
  Коммиты: 7 шт (e7203dd..a809005), conventional. Не запушено.
  Отклонения от PLAN.md: (1) код анализа характеристик вошёл в коммит шага 1 (скрипт писался целиком), коммит шага 2 несёт тесты атрибутов/ссылок; (2) два дополнительных коммита — feat (numeric-кандидаты по Owner_Key, min_row_balance) и fix (буквенная единица в кандидатах) по фактуре прогона сэмплов; (3) фактическое число JSON в сэмплах — 17, не 20.
  Блокеры: нет. Следующий шаг: code-reviewer → QA gate → PR; шаг 5 (живой MinIO) после мёрджа PR #125.
  Дополнение (шаг 5, после мёрджа PR #125): origin/main вмержен (3ca9fb9, конфликтов нет). Живой MinIO — контейнер `backend-minio-1` (сеть backend_default, не порт-exposed; endpoint 172.18.0.3:9000, dev-creds minioadmin из compose), бакет `onec-intake` (env `MINIO_INTAKE_BUCKET`, ключи `YYYY/MM/DD/HHmmss_<uuid4>.bin`). Прогон `--minio` → `docs/onec/reports/2026-07-30_minio-onec-intake.md/.json`: 2 ZIP-пакета CommerceML (import+offers, мок Фазы 7, по 5 товаров) — сниффинг/распаковка/роли отработали, unknown нет. OData-выгрузок живьём пока не было; дельта зафиксирована в FORMAT_MAP.md (расхождений с разделом 6 нет). Коммит 3923e61. pytest 32/32, ruff чисто. Полный `make test-backend` (docker): 414 passed, 1 skipped (skip = наш модуль, т.к. в контейнер монтируется только backend/).

### 2026-07-30 | implement (backend-dev) | onec-mock-server-0730 — EXECUTE DONE, готово к ревью
  Issue #124 (Фаза 7 эпика #117). Worktree `.worktrees/onec-mock-server-0730`, ветка `feature/onec-mock-server-0730`.
  Что сделано (строго по PLAN.md, 8 шагов = 8 коммитов по чек-листу issue):
  - Новый standalone-сервис `mocks/onec-server/` (FastAPI + APScheduler в одном процессе, без Celery/Redis; импортов backend нет, D-01): Dockerfile, requirements, ruff-конфиг, `Settings` по env (D-10).
  - Виртуальный каталог в PG-схеме `onec_mock` (D-03): модели categories/attributes/products/product_attribute_values/change_log/sent_changes/scenario_runs, `CREATE SCHEMA IF NOT EXISTS` + create_all на старте (без Alembic), детерминированный seeder (CATALOG_SEED=42, 200 товаров). Схема конфигурируема env `ONEC_MOCK_SCHEMA` (тесты → `onec_mock_test`).
  - Генератор CommerceML 2.x за интерфейсом `PackageGenerator` (D-05): валидный 2.10, `СодержитТолькоИзменения="true"`, Классификатор/Каталог/Предложения, `ПометкаУдаления` для удалённых, ZIP import.xml+offers.xml (D-02).
  - 7 детерминированных сценариев мутаций (D-06) с журналом `scenario_runs`; ROUND_HALF_UP для цен, stock ≥ 0.
  - Sender (D-07): httpx, заголовки по D-02, успех 200/202 → batch_id в change_log + sent_changes(success); сбой → retry backoff 1/5/15 мин (max 3/тик, sleep инъектируем), pending сохраняется; `package_zip` в sent_changes для duplicate_batch; resend_last + corrupt_checksum.
  - API управления (D-08, без auth): POST `/trigger/`, POST `/scenario/` (422 на неизвестный), GET `/status/`, GET `/history/` (limit ≤100, offset) — trailing slash везде.
  - Тесты: 27 pytest против Docker-PG (схема `onec_mock_test`, DROP per test), MockTransport + fake clock; Makefile `test-onec-mock`/`lint-onec-mock` (VENV из основного репо).
  - Infra (D-09): сервис `onec-mock` в backend/docker-compose.yml (порт 8100); helm onec-mock-{deployment,service}.yaml за `onecMock.enabled` (default false; test=true, prod=false), ClusterIP, без ingress, ONEC_API_KEY ← secretKeyRef promelectron-secrets/ONEC_WEBHOOK_API_KEY; CI build/push образа `promelectron-onec-mock` в deploy.yml + `--set onecMock.image` в test-деплое; SOPS TODO дополнен; README мока, ссылка в docs/onec/HTTPService_PromElektron.md, PROJECT_CONTEXT.md, .env.example.
  Проверки: pytest 27/27 ✅, ruff чисто ✅, `helm template` test рендерит Deployment+Service мока / prod не рендерит ✅, `docker compose config` ✅, backend/src и frontend не затронуты ✅. Не запушено.
  Отклонения от PLAN.md: нет (в т.ч. решение по открытому вопросу — onec-mock в compose добавлен на шаге 8, тесты на хосте из venv).
  Известные ограничения: end-to-end стыковка с intake возможна после мержа Фазы 1 (#118); ротация change_log/sent_changes — ручная (out of scope по спеке).
  Блокеры: нет. Следующий шаг: code-reviewer → QA gate → PR.

### 2026-07-30 | implement (backend-dev) | onec-universal-intake-0720 — EXECUTE DONE, готово к ревью
  Issue #118 (Фаза 1 эпика #117). Worktree `.worktrees/onec-universal-intake-0720`, ветка `feature/onec-universal-intake-0720`.
  Что сделано (строго по PLAN.md, шаги 1–11):
  - Модель `OnecIntakeLog` (`onec_intake_log`, гибрид D-07: base + `headers`/`query_params` JSONB + `error` Text, status default `received`) + миграция `937fc6751168` (autogenerate прицепил drift — миграция вычищена вручную до create_table + 3 индекса; upgrade/downgrade/upgrade проверены).
  - `MINIO_INTAKE_BUCKET` (default `onec-intake`) в `config.py`, `.env.example`, `docker-compose.yml` (api + job-worker).
  - `upload_raw(key, data, content_type, bucket=None)` в StorageService Protocol + обе реализации; `_ensure_bucket`/`get_url` обобщены параметром bucket; provisioning ленивый (D-03).
  - `onec_intake_service.py`: `INTAKE_MAX_BODY_BYTES` (100 МБ, monkeypatchable), потоковое чтение `request.stream()` → sha256 инкрементально + `SpooledTemporaryFile(16MB)`, 413 по Content-Length (early) и по факту (ничего не сохраняется); ключ `YYYY/MM/DD/HHmmss_<uuid4>.bin` (UTC); `X-1C-Api-Key` исключён из сохраняемых headers.
  - Endpoint `POST /api/v1/onec/intake/` (202, `OnecIntakeResponse{intake_id, received_bytes}`, auth `X-1C-Api-Key` + `conditional_limit("100/minute")`, `request: Request` в сигнатуре).
  - 11 тестов `test_onec_intake.py` (D-11 + XML + пустое тело + unit-тесты early/stream 413) — зелёные.
  - Новый path-scoped ingress `api-ingress-onec.yaml` (`/api/v1/onec`, 100m; глобальный 10m не тронут); `helm template` (default/test/prod values) рендерится.
  - Дока для 1С `docs/onec/INTAKE_ENDPOINT.md`; строка в PROJECT_CONTEXT.md → API Inventory (новая секция «1С интеграция»).
  Коммиты: 9 шт (conventional, по одному на пункт чек-листа issue), от `d01ffab` до HEAD. Не запушено.
  Отклонения от PLAN.md: нет. Известные ограничения (из Risks): `upload_raw` читает spool в bytes для `put_object` (пик памяти до 100 МБ/запрос — допустимо для Фазы 1); `remote_addr` за ingress = IP контроллера.
  Блокеры: нет. Следующий шаг: code-reviewer → QA gate → PR.

### 2026-07-20 | планирование (оркестратор) | catalog-meilisearch — эпик и подзадачи на GitHub
  По указанию пользователя: только issue, БЕЗ реализации. Создан эпик #117 «Каталог с 1С-синхронизацией и Meilisearch» + 5 подзадач, все добавлены на project board:
  - #118 Фаза 1: intake-эндпоинт (raw → MinIO) + лимит body 100 МБ (лимит согласован пользователем; сейчас ingress 10m — зафиксировано в issue)
  - #119 Фаза 3: анализатор форматов + карта маппинга (docs/onec/FORMAT_MAP.md)
  - #120 Фаза 4: модель атрибутов + загрузчик из MinIO в каталог
  - #121 Фаза 5: Meilisearch — инфра, индексация (swap), /api/v1/search/ с фасетами
  - #122 Фаза 6: frontend — панель фасетных фильтров за feature flag
  Каждая подзадача содержит чек-лист с правилом «после каждого пункта — отдельный коммит» (с готовыми commit message), Must-haves, AC, Out of Scope, техзаметки для будущего агента (переиспользуемые модули, trailing slash, тесты в Docker, запрет ходить в продовую 1С).
  Также в этой сессии: подтверждено, что архив в Загрузках содержит реальные OData-выгрузки продовой УНФ (март 2026, старый прототип ходил туда только на чтение GET); созданы sequence-диаграммы флоу в docs/flows/ (6 шт, mmd+svg+png), incl. детальную catalog-1c-sync-detailed.
  Блокеры: нет. Следующий шаг: старт Фазы 1 (#118) и Фазы 3 (#119) по одобрению пользователя.

### 2026-07-20 | spec (оркестратор) | catalog-meilisearch-filters-1c-0720 — SPEC READY
  Запрос: тимлид (IT Александр, Telegram 10.07) — спроектировать каталог: синхронизация с 1С, категории/подкатегории, поиск и фасетные фильтры по атрибутам на Meilisearch. Только спецификация для обсуждения.
  Что сделано:
  - Создана координационная плоскость `.agent/runs/catalog-meilisearch-filters-1c-0720/` (task.md).
  - Research fan-out (4 explore-субагента): libraries, best-practices, codebase-integration, external-api-docs → `research/*.md`.
  - Архитектор (plan-субагент) синтезировал спецификацию → `spec.md`, **Status: READY**.
  Ключевые решения (D-01..D-12): модель атрибутов — гибрид справочник+typed values (не чистый EAV, не JSONB); Meilisearch v1.50; доступ к поиску — бэкенд-прокси `GET /api/v1/search/` (не vue-instantsearch из браузера); официальный sync `meilisearch` SDK + `asyncio.to_thread`; характеристики 1С — поле `attributes` в `product`-change (расширение `docs/onec/HTTPService_PromElektron.md`); индексация через `job_worker` (partial update + full reindex со swap); миграция с ILIKE-поиска через feature flag; helm-тройка для meilisearch.
  Важный факт: 1С-конвейер уже зрелый (webhook → OnecChangeLog → Job → job_worker), атрибутов у товаров нет вообще, поиск сейчас ILIKE. ADR-014 (tsvector) будет superseded.
  Блокеры: нет. Assumptions на подтверждение тимлиду: мастер атрибутов — 1С (auto-create), объём 10–100K SKU, без таблицы category_attributes.
  Следующий шаг: обсуждение spec с пользователем/тимлидом → реализация через /skill:implement.

### 2026-07-18 | implement (оркестратор) | fix-e2e-cart-in-stock — MERGED
  Запрос пользователя: «деплой тесты упали проверь» после merge PR #113/#114. Issue #115.
  Что сделано:
  - Worktree `.worktrees/fix-e2e-cart-in-stock`, ветка `fix/e2e-cart-in-stock` от `origin/main`.
  - `frontend/src/components/ProductCard.vue`: добавлен `data-product-id`.
  - `frontend/e2e/helpers.js`: helper `getInStockProductCard(page)` выбирает через API товар с максимальным stock.
  - Обновлены E2E-спеки: `catalog.spec.js`, `pdp.spec.js`, `checkout.spec.js`, `checkout-failed-cards.spec.js`, `cdek-widget.spec.js` — используют helper.
  - `frontend/src/components/CdekDeliveryWidget.vue`: режим `window.__CDEK_MOCK_MODE__` для работы без Yandex Maps API key.
  - Проверки:
    - Frontend unit tests: 271 passed ✅
    - Frontend lint: passed ✅
    - Полный E2E-suite: 100 passed, 2 flaky (retry прошёл), финальный статус зелёный ✅
  - PR #116 влит в main (merge commit `e1172a23c38ab5f67ba433a324011c4c74d6ddf8`) по одобрению пользователя. Issue #115 → Done.
  Блокеры: нет.

### 2026-07-18 | implement (оркестратор) | fix-e2e-auth-after-guest-checkout — MERGED, follow-up infra memory
  Запрос пользователя: «деплой тесты упали проверь» после merge PR #111 (remove-guest-checkout). Issue #112.
  Этап 1 — кодовый фикс:
  - Worktree `.worktrees/fix-e2e-auth-after-guest-checkout`, ветка `bugfix/fix-e2e-auth-after-guest-checkout` от `origin/main` (c6a45ca).
  - PLAN.md одобрен пользователем.
  - `frontend/src/views/Login.vue`: `mergeCartOnLogin()` запускается в фоне (`.catch`), не блокируя редирект.
  - `frontend/src/views/Register.vue`: аналогично.
  - `frontend/src/composables/useAuth.js`: `logout()` очищает `guest_cart` из localStorage.
  - `frontend/e2e/auth.spec.js`: `test.beforeEach` очищает cookies/localStorage, получает реальный продукт через API, убран hard-coded `Test Product`, добавлены `waitForURL` и таймауты.
  - `frontend/src/__tests__/Register.spec.js`: mock `mergeCartOnLogin` возвращает `Promise.resolve()`.
  Проверки:
  - `npm run lint` в `frontend` — 0 warnings/errors ✅
  - `npm test` в `frontend` — 271 passed ✅
  - Локальный E2E `auth.spec.js` — 3 последовательных прогона по 3 passed ✅
  - Pre-push check при push — lint backend/frontend пройден ✅
  - PR #113 влит в main (merge commit `c724c6a`) по одобрению пользователя. Issue #112 → Done.
  Этап 2 — анализ CI-фейла после merge:
  - CI run `29638418697`: job `test-e2e / e2e` failed.
  - Скриншоты/логи: формы регистрации/входа показывают «Ошибка регистрации. Попробуйте позже.» / «Ошибка входа. Проверьте данные.»
  - Прямой вызов `POST /api/v1/register/` возвращает 500.
  - `kubectl describe pod -n promelectron-test promelectron-api-...`: контейнер API был OOMKilled (Exit Code 137) с лимитом 256Mi; после перезапуска ErrImagePull/BackOff.
  - Корень: в test-окружении лимит памяти API 256Mi недостаточен под нагрузку E2E.
  Этап 3 — infra fix:
  - Worktree `.worktrees/fix-test-api-memory`, ветка `fix/test-api-memory`.
  - `infra/helm/stage/test/values.yaml`: API resources переопределены на 256Mi request / 512Mi limit.
  - PR #114: https://github.com/AutonomaCo/promelectron/pull/114
  Блокеры: нет.


## 2026-08-29 — toast-follow-scroll (Issue #194)
- Задача: toast-уведомления не следовали за скроллом.
- Root cause: `overflow-x: hidden` на `html`/`body` (`frontend/src/assets/base.css:18,57`) делал их scroll-контейнерами и ломал `position: sticky` хедера (Header.vue:200), к которому якорится `.header__toast`.
- Fix (вариант A, одобрен пользователем): `overflow-x: clip` с fallback-строкой `overflow-x: hidden` на html и body (Safari < 16 — старое поведение без регресса).
- Worktree `.worktrees/toast-follow-scroll`, ветка `bugfix/toast-follow-scroll`, коммит `6765159`.
- Регрессионный тест: новая Playwright-спека `frontend/e2e/toast-follow-scroll.spec.js` (header sticky после скролла + toast в viewport; mobile 390x844 + desktop 1280x900).
- Проверки (локально, host Playwright против dev-сервера worktree :5199 и API-контейнера :8000):
  - Спека ДО фикса: 4 failed (toast y=-363 вне viewport) ✅ воспроизведение
  - Спека ПОСЛЕ фикса: 4 passed ✅
  - `responsive.spec.js` (no horizontal scroll): 67 passed ✅
  - `make test-frontend`: 380 passed ✅; `make lint-frontend`: 0 warnings/errors ✅
- Полный `make test-e2e` не запускался (поднимает весь стек; прогнаны целевые спеки напрямую). PLAN.md без отклонений.
- Блокеры: нет.
- Review: APPROVED (1 minor + 2 nit исправлены и VERIFIED; F003 nit про z-index тостов/модалок — кандидат на отдельную задачу).
- PR #196: https://github.com/AutonomaCo/promelectron/pull/196 (Closes #194), issue #194 → In review на project board.
- `make pre-push`: lint зелёный; backend unit упал на 48 errors `InvalidCatalogNameError: template database "promelectron_test_template" does not exist` — инфра окружения (нет template DB в локальном postgres), не связано с diff (frontend-only). Frontend unit (380), e2e-спека (4/4), responsive (67/67) — зелёные из прогона разработчика.
- Урок записан в `.kimi-code/LESSONS_LEARNED.md` (overflow-x:hidden ломает sticky; CSS-раскладку покрывать E2E; Playwright click auto-scroll).


## 2026-08-29 — cart-button-state (Issue #198)
- Задача: заменить toast-уведомления успеха на персистентное состояние кнопки корзины.
- Решения (одобрены пользователем): кнопка «В корзину» → «В корзине · N» зелёной (`--color-success`), повторный клик → /cart; скоуп ProductCard + ProductDetail; тосты успеха избранного убраны, error-тосты остались.
- Реализация: useCart расширен reactive map `cartQuantities` (`getQuantityInCart`/`isInCart`; guest — localStorage, auth — один GET /cart/ при init + синк на мутациях); `--color-success: #34C759` в base.css; контракт cartCount обратно совместим.
- Review: iteration 1 FIXES_NEEDED (F001 blocker — пропущенные e2e checkout-спеки с ожиданием .toast--success; F002/F003 minor/nit) → все FIXED → iteration 2 APPROVED/VERIFIED.
- QA: TESTS_PASSED — vitest 395/395, lint чист, e2e 11+3+5 passed, ручная проверка AC (guest: add → «В корзине · 1» → /cart → удаление → «В корзину»; reload-персистентность; PDP-консистентность; ноль лишних запросов при скролле).
- PR #201: https://github.com/AutonomaCo/promelectron/pull/201 (Closes #198), issue → In review. `make pre-push` пропущен осознанно: BLK-015 (нет template DB локально), diff frontend-only.
- Урок записан в `.kimi-code/LESSONS_LEARNED.md` (grep всех e2e по удаляемым селекторам; API_URL для host-прогонов).
- 2026-08-29: Оба PR влиты пользователем в main — #196 (toast-follow-scroll, issue #194 → Done) и #201 (cart-button-state, issue #198 → Done). Конфликтов не было.


## 2026-08-29 — S002: экранирование в email-шаблонах
- Задача: S002 (LOW) — неэкранированные `product_name`/`shipping_address` в HTML email-шаблонах (пре-существующее, из review).
- Проверка finding: подтверждён. `product_name` из `Product.name` (контент поставщика) и `shipping_address` (ввод пользователя) вставлялись сырыми в HTML письма подтверждения заказа (`email_service.py`); письма уходят покупателю (`order_service.py`, `payment_service.py`).
- Fix: `html.escape()` для `product_name` в `_order_items_html()` и `shipping_address` в `send_order_confirmation()`. Текстовая версия письма не трогается (экранирование не нужно).
- Тест: `test_send_order_confirmation_escapes_html_injection` — `<script>`/`<img onerror>` в имени товара/адресе экранируются в HTML, text-body остаётся сырым.
- Проверки: `pytest tests/test_email.py` — 15/15 passed (с `DATABASE_URL` на локальный postgres; без него фикстура `test_session` падает на JSONB/SQLite — пре-существующее, BLK-015). Ruff по изменённым файлам чист (F401 в test_email.py:6 — пре-существующий, не тронут).
- Issue #202 создан (board → In review), ветка `bugfix/s002-email-escaping`, коммит `29db010`, PR #203: https://github.com/AutonomaCo/promelectron/pull/203
- `make pre-push` (E2E) не запускался — backend-only diff, осознанно (BLK-015); lint-backend покрывает только `src/` — чист.


## 2026-08-29 — E2E: разбор падения после merge #201 + фикс (Issue #204)
- Run 33250956496 (merge #201 → main), job `test-e2e / e2e` failed, 9 тестов. Логи actions недоступны (i/o timeout до results-receiver), разбор по playwright-report из артефактов.
- Классификация: toast-follow-scroll (desktop+mobile) — реальная регрессия (#196 спека ждёт `.toast--success`, #201 удалил success-тосты корзины; review #201 починил checkout-спеки, эту пропустил). auth/profile/cart-select — флейки: API pod unresponsive (readiness `/health` timeouts при старте e2e), под пересоздан после прогона; кластер перегружен (cronjob CDEK `3 Insufficient cpu` каждые 5 мин). checkout Mir — внешний yoomoney.ru. cdek-widget/checkout-failed-cards — flaky helper.
- Перезапуск (`gh run rerun --failed`) подтвердил: auth/profile/cart-select прошли; стабильно падают toast-follow-scroll и admin (`waitForResponse` 30s — API тормозил); новое падение checkout-failed-cards (кнопка продукта 28 disabled → «В корзину»).
- Fix (worktree `.worktrees/fix-e2e-specs`, ветка `bugfix/e2e-specs-fixes`, коммит `7ce3779`):
  - `toast-follow-scroll.spec.js`: триггер success-тоста заменён на загрузку аватара в /profile/edit; проверка позиционирования на sticky-хедере (#194) сохранена.
  - `helpers.getInStockProductCard`: `limit=100` + пересечение с отрисованными `[data-product-id]` на странице, max-stock среди них.
- Проверки локально (host Playwright → vite :5199 + uvicorn :8000 из worktree, БД `promelectron_e2e` на dev-postgres, SEED_SECRET=dev placeholder): toast-follow-scroll 4/4, catalog+pdp 6/6 (4 facet skipped по флагу), cdek-widget 5/5. checkout-failed-cards локально не гонялся (нет YooKassa creds) — его падавший участок это тот же helper. ESLint/oxlint e2e/ не покрывают (ignore).
- Issue #204 (board → In review), PR #205: https://github.com/AutonomaCo/promelectron/pull/205
- Хвосты: БД `promelectron_e2e` оставлена в dev-postgres (можно дропнуть); перегруз test-кластера (CPU) и flaky admin — отдельная infra-тема; node_modules скопирован в worktree из корня (gitignored).
- Infra-issue #206 заведён (board → Backlog): перегруз test-кластера по CPU, флейки auth/admin/cart-select, CDEK cronjobs `Insufficient cpu`/`DeadlineExceeded`. Label `infra` в репо нет — создан без label.
- Scratch-БД `promelectron_e2e` дропнута из dev-postgres.
- 2026-08-29: Оба PR влиты пользователем в main. PR #203 потребовал merge origin/main (ветка была от устаревшего local main): конфликт с #200 (S001 `html_escape` + новый шаблон `send_order_paid` с той же дырой S002) — резолв: алиас `html_escape`, экранирование добавлено и в `send_order_paid`, +тест инъекции для него; 20/20 email-тестов зелёные, коммит резолва `4a5277e`. PR #205 влит без конфликтов. Issues #202/#204 → Done. Deploy+e2e run 33257162752 на main запущен — жду результат для подтверждения фикса #204.

## 2026-08-29 — доводка e2e после merge #205
- GitHub-токен протух mid-session (keyring invalid) → пользователь выдал новый PAT (scopes: repo, workflow, project, admin:org, write:packages), `gh auth login --with-token` — восстановлено.
- Run 33257162752 (merge #205 на main): **toast-follow-scroll 4/4 прошёл** — регрессия #204 закрыта; admin тоже зелёный. НО упали 4/5 cdek-widget с `No in-stock product rendered on the page` — гонка в моём фиксе #205: `evaluateAll [data-product-id]` до асинхронного рендера каталога на медленном CI → пустое пересечение. Локально не воспроизводилось.
- Fix: `expect(first [data-product-id]).toBeVisible()` перед evaluateAll. Worktree `.worktrees/fix-e2e-helper-wait`, ветка `bugfix/e2e-helper-wait`, коммит `b250469`.
- Проверка локально (тот же стенд: uvicorn :8000 + vite :5199, БД promelectron_e2e): cdek-widget + catalog + pdp + toast-follow-scroll — 15/15 passed (4 facet skipped по флагу).
- PR #207: https://github.com/AutonomaCo/promelectron/pull/207 (Refs #204). Оставшиеся падения run'а (cart-select 400, profile register, checkout Mir/invalid_csc) — флейки окружения (#206).
- Урок: helper'ы, читающие DOM через evaluateAll, обязаны ждать рендера — `expect().toBeVisible()` до snapshot'а; локально гонка не ловится, проверять мысленно на медленном CI.

## 2026-08-29 — Infra: стабилизация test-окружения (Issue #206)
- Диагностика read-only (kubectl get/describe, nodes stats): workers 98–99% CPU **requests**, реальное usage ~9% — проблема в шедулинге (requests over-commit), не в рантайме. Болезнь API = троттлинг на limit 500m под bcrypt-всплесками e2e-регистраций + дефолтный probe timeout 1s → readiness флап → 5xx в тестах.
- Fix (worktree `.worktrees/fix-test-infra`, ветка `bugfix/test-infra-resources`, коммит `c70a9e8`): probes `timeoutSeconds: 5` в api-deployment.yaml; test values — API limits cpu 1000m / memory 768Mi (requests не тронуты: limits не влияют на шедулинг); CDEK cronjobs на test */5+*/15 → */30.
- Проверка: `helm template` с test values — 29 манифестов, probes/limits/schedules корректны.
- PR #208: https://github.com/AutonomaCo/promelectron/pull/208 (Refs #206). В кластер руками не лезли — применит CI deploy.
- 2026-08-29: PR #207 (e2e-helper wait) и #208 (infra test resources) влиты пользователем в main. Запущен фоновый watch run 33259450261 (merge #208 → deploy test с новыми values + e2e) — по результату отчёт и решение по закрытию #206.
- Run 33259450261 (merge #208): ПОЛНОСТЬЮ ЗЕЛЁНЫЙ — build/deploy-test/migrate-check/seed/smoke/**e2e** success. Флейки ушли после #207+#208. Issue #206 закрыт с комментарием (board → Done); кластерный CPU over-commit — чужая сторона, наша mitigated.
- Cleanup: worktree'ы fix-e2e-specs/fix-e2e-helper-wait/fix-test-infra удалены, локальные и remote ветки 4 bugfix/* удалены, main checkout переключён на main и fast-forward до f37f413. Старые чужие worktree'ы (.worktrees/e2e-cart-select-race и др.) не трогал.


## 2026-08-29 — коммит конфигов агентов + очистка worktree + фикс cleanup
- Коммит `8b72e54` (main, запушен): skills/rules/AGENTS, SESSION_LOG + archive, хуки, пайплайн-хелперы, BLOCKERS/LESSONS.
- Очищены все устаревшие worktree (6 зарегистрированных + 6 осиротевших каталогов, ~1.6 ГБ); ветки кроме main/recovery-local удалены. Понадобился docker chown — root-owned файлы от контейнерных прогонов.
- Фикс `implement-pipeline.py`: `_remove_tree()` без ignore_errors + docker-chown fallback; cleanup/janitor больше не рапортуют ложный успех. Урок в LESSONS_LEARNED.

## 2026-09-08 — onec-odata-real-catalog-0908 (issue #227): переход на OData pull + реальный каталог
- Решение владельца: финальная архитектура обмена с 1С:УНФ — **OData pull** (не CommerceML push). Данные — мартовский дамп реальной 1С `1c.74bita.ru/UNF-PromElektron` (1523 товара из ~10К каталога; цены/атрибуты/остатки ссылаются и за его пределы).
- Мок `mocks/onec-server/` переписан из CommerceML-симулятора в **OData-сервер** поверх PG-схемы `onec` (сид `data/onec_seed.sql.gz`, gitignored; курация: последние цены per вид/товар, 364K→82K строк). 10 сущностей, `$top/$skip/$filter`, Basic Auth, `odata.error`, placeholder-JPEG по `$value`. 23 теста ✅.
- Backend: `onec_client` + `onec_sync_service` — категория по `КатегорияНоменклатуры_Key` (не Parent_Key), вес кг→г, DeletionMark→is_active, синк характеристик (Attribute/ProductAttributeValue) и изображений (MinIO → products.images), исправлен фильтр склада (`СтруктурнаяЕдиница_Key` вместо `Склад_Key`), per-change savepoints (битый change не валит батч), дубли SKU → sku=NULL+strip, сквозная агрегация остатков по страницам.
- Живые прогоны против мока: каталог загружен и сверен с дампом — 1343 товара (1328 активных = точное подмножество), 31 категория, 15405 цен, 5535 значений характеристик (= мартовскому логу), изображения у 922, остатки сошлись 0/0 расхождений по round(sum). Найдено и починено 3 бага: дубли SKU валили батч, частичная агрегация остатков + staleness, нестабильный ORDER BY пагинации мока (964 потери/дубли на 5244 строках).
- **H-001 решён**: сайтовый вид цен — «Розница» `3d3bea35-5d6a-11eb-948a-f81a67046005` (решение владельца); price_type пишется реальными GUID сразу.
- Follow-up (не в объёме): удаление CommerceML-ветки лоадера и push-эндпоинтов, инкрементальный синк, helm values onecMock, секреты ONEC_MOCK_* в test, деплой на test.
