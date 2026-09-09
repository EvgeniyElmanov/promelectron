#!/usr/bin/env bash
# CI-оркестратор сидинга каталога электротоваров на test-стенде (issue #147,
# переписан под OData pull в #227).
#
# Цепочка: cleanup → reseed users/supplier → restart api → проверка сида мока
# (схема onec, ~220 SKU — дамп реальной 1С, сокращён 2026-09-09 с ~1523 для
# скорости CI; полный бэкап: mocks/onec-server/data/onec_seed_full_backup_20260909.sql.gz)
# → POST /admin/onec/full-sync/ →
# ожидание ONEC_FULL_SYNC + ONEC_APPLY_CHANGES → фасеты (is_filterable по имени
# атрибута, коды = GUID) + full reindex Meilisearch → реальные фото → верификация.
#
# Схему onec сид-скрипт НЕ пересоздаёт: сид (mocks/onec-server/data/onec_seed.sql.gz,
# gitignored) загружается в test-БД вручную один раз; cleanup_test_env.py чистит
# только public-таблицы и legacy-схему onec_mock.
#
# Запускается из job'а seed-test-catalog в deploy.yml (self-hosted runner с kubeconfig).
# Только test-окружение: cleanup_test_env.py защищён env-флагом + --confirm (D-02).
set -euo pipefail

NS="${NS:-promelectron-test}"
API="${API:-https://api.promelectron-test.aidrivencode.ru}"
# F006/S001: секреты обязательны из env (GitHub Secrets в deploy.yml), хардкод-дефолтов нет.
: "${SEED_SECRET:?SEED_SECRET не задан — пробросьте из GitHub Secret SEED_SECRET}"
: "${SEED_ADMIN_PASSWORD:?SEED_ADMIN_PASSWORD не задан — пробросьте из GitHub Secret SEED_ADMIN_PASSWORD}"
: "${SEED_SUPPLIER_PASSWORD:?SEED_SUPPLIER_PASSWORD не задан — пробросьте из GitHub Secret SEED_SUPPLIER_PASSWORD}"
ADMIN_EMAIL="${SEED_ADMIN_EMAIL:-seed-admin@example.com}"
ADMIN_PASSWORD="$SEED_ADMIN_PASSWORD"
# Ожидание сида мока: схема onec в test-БД (загружается вручную из
# onec_seed.sql.gz), 220 номенклатур после сокращения 2026-09-09 (было 1523).
# 200 — нижняя граница «сид на месте».
EXPECTED_PRODUCTS=200
MIN_PRODUCTS=25        # нижняя граница Acceptance Criteria
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

PF_PIDS=()

log()  { echo "[seed-catalog $(date +%H:%M:%S)] $*"; }

psql_query() {
  kubectl exec deploy/promelectron-postgresql -n "$NS" -- \
    sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "$1"' sh "$1"
}

diagnostics() {
  log "=== ДИАГНОСТИКА ==="
  kubectl get pods -n "$NS" -o wide || true
  log "--- jobs (последние 10) ---"
  psql_query "SELECT job_type, status, attempts, left(array_to_string(processing_log, ' | '), 800) FROM jobs ORDER BY id DESC LIMIT 10" || true
  log "--- onec_intake_log (последние 5) ---"
  psql_query "SELECT id, status, left(coalesce(error, ''), 300) FROM onec_intake_log ORDER BY id DESC LIMIT 5" || true
  log "--- logs: api ---"
  kubectl logs -n "$NS" -l app=promelectron-api --tail=100 || true
  log "--- logs: job-worker ---"
  kubectl logs -n "$NS" -l app=promelectron-job-worker --tail=100 || true
  log "--- logs: onec-mock ---"
  kubectl logs -n "$NS" -l app=promelectron-onec-mock --tail=100 || true
}

fail() {
  echo "[seed-catalog] FAIL: $*" >&2
  diagnostics
  exit 1
}

cleanup() {
  for pid in "${PF_PIDS[@]:-}"; do
    [ -n "$pid" ] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

# wait_for <описание> <timeout_sec> <функция-проверка>
wait_for() {
  local desc="$1" timeout="$2" fn="$3"
  log "ожидание: ${desc} (timeout ${timeout}s)"
  local deadline=$((SECONDS + timeout))
  while (( SECONDS < deadline )); do
    if "$fn"; then
      log "OK: ${desc}"
      return 0
    fi
    sleep 10
  done
  fail "таймаут ожидания: ${desc}"
}

port_forward() { # <svc> <port>
  kubectl port-forward "svc/$1" "$2:$2" -n "$NS" >/dev/null 2>&1 &
  PF_PIDS+=($!)
  # ждём, пока порт начнёт отвечать
  local deadline=$((SECONDS + 30))
  while (( SECONDS < deadline )); do
    curl -sf -o /dev/null "http://localhost:$2/" && return 0
    sleep 2
  done
  return 0  # некоторые сервисы не отвечают на / — дальше poll по реальному endpoint'у
}

# --- Проверки для wait_for ---

check_mock_seeded() {
  # Формат /status/ OData-мока (#227): {"status","schema","tables":{<table>:count}}
  curl -sf "http://localhost:8100/status/" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d['tables']['products'] >= ${EXPECTED_PRODUCTS} else 1)" \
    2>/dev/null
}

check_full_sync_done() {
  [ "$(psql_query "SELECT status FROM jobs WHERE job_type='ONEC_FULL_SYNC' ORDER BY id DESC LIMIT 1" 2>/dev/null)" = "completed" ]
}

check_apply_jobs_settled() {
  # Все батчи применены: нет pending/processing; failed считаем отдельно в verify
  [ "$(psql_query "SELECT count(*) FROM jobs WHERE job_type='ONEC_APPLY_CHANGES' AND status NOT IN ('completed','failed')" 2>/dev/null)" = "0" ] 2>/dev/null
}

check_no_failed_apply() {
  [ "$(psql_query "SELECT count(*) FROM jobs WHERE job_type='ONEC_APPLY_CHANGES' AND status='failed'" 2>/dev/null)" = "0" ] 2>/dev/null
}

check_reindex_done() {
  [ "$(psql_query "SELECT count(*) FROM jobs WHERE job_type='SEARCH_REINDEX_FULL' AND status='completed'" 2>/dev/null)" -ge 1 ] 2>/dev/null
}

check_meili_docs() {
  curl -sf -H "Authorization: Bearer ${MEILI_KEY}" "http://localhost:7700/indexes/products/stats" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('numberOfDocuments', 0) >= ${MIN_PRODUCTS} else 1)" \
    2>/dev/null
}

api_login() { # <email> <password> → печатает access_token
  curl -sf -X POST "$API/api/v1/login/" \
    -H 'Content-Type: application/json' \
    -d "{\"email\": \"$1\", \"password\": \"$2\"}" | python3 -c \
    "import json,sys; print(json.load(sys.stdin)['access_token'])"
}

# ============================== ШАГИ ==============================

log "=== Шаг 1/10: cleanup окружения $NS ==="
kubectl exec deploy/promelectron-api -n "$NS" -- \
  python /app/scripts/cleanup_test_env.py "--confirm=$NS" \
  || fail "cleanup_test_env.py завершился с ошибкой"

log "=== Шаг 2/10: reseed users/supplier ==="
# ВАЖНО: /api/v1/seed БЕЗ trailing slash (legacy, иначе 307)
curl -sf -X POST "$API/api/v1/seed" -H "x-seed-secret: $SEED_SECRET" \
  || fail "POST /api/v1/seed не удался"
SUPPLIER_ID="$(psql_query "SELECT id FROM suppliers WHERE api_key='seed-supplier-api-key'")"
# Guard D-06: intake-товары привязываются к ONEC_DEFAULT_SUPPLIER_ID=1
[ "$SUPPLIER_ID" = "1" ] || fail "guard D-06: seed-supplier id=$SUPPLIER_ID, ожидался 1"
log "guard D-06: seed-supplier id=1 — OK"

log "=== Шаг 3/10: rollout restart api ==="
# api — стирает local uploads (emptyDir); мок не рестартуем: сид в схеме onec
# переживает рестарты, а deploy-test уже выкатил свежий образ мока
kubectl rollout restart deployment/promelectron-api -n "$NS"
kubectl rollout status deployment/promelectron-api -n "$NS" --timeout=180s \
  || fail "api не поднялся после restart"

log "=== Шаг 4/10: проверка сида мока (схема onec, >= ${EXPECTED_PRODUCTS} SKU) ==="
port_forward promelectron-onec-mock 8100
wait_for "мок видит сид каталога" 120 check_mock_seeded

log "=== Шаг 5/10: триггер pull-синка из мока (POST /admin/onec/full-sync/) ==="
ADMIN_TOKEN="$(api_login "$ADMIN_EMAIL" "$ADMIN_PASSWORD")" \
  || fail "login seed-admin не удался"
SYNC_OUT="$(curl -sf -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$API/api/v1/admin/onec/full-sync/")" \
  || fail "POST /admin/onec/full-sync/ не удался (ONEC_API_URL/креды мока в секрете?)"
echo "$SYNC_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'[seed-catalog] full-sync: {d}'); sys.exit(0 if d.get('status') == 'queued' else 1)" \
  || fail "full-sync вернул не queued: $SYNC_OUT"

log "=== Шаг 6/10: ожидание pull-синка (ONEC_FULL_SYNC + батчи, timeout 1800s) ==="
wait_for "job ONEC_FULL_SYNC completed" 1800 check_full_sync_done
# apply-батчи идут на одном job-worker'е с троттлингом по CPU limit — при росте
# каталога 900s уже не хватало (run 34350753192); 1800s даёт запас, чтобы CI
# не зависел от объёма каталога
wait_for "все ONEC_APPLY_CHANGES settled" 1800 check_apply_jobs_settled
check_no_failed_apply || fail "есть failed ONEC_APPLY_CHANGES job'ы"
PRODUCTS_TOTAL="$(psql_query "SELECT count(*) FROM products")"
[ "${PRODUCTS_TOTAL:-0}" -ge "$MIN_PRODUCTS" ] \
  || fail "после синка товаров=$PRODUCTS_TOTAL, ожидалось >= $MIN_PRODUCTS"
log "pull-синк завершён: товаров=$PRODUCTS_TOTAL"

# Алиас сайтового вида цены. Helm test-values задают ONEC_SITE_PRICE_TYPE=BASE
# (наследие CommerceML-эпохи), а OData-синк пишет price_type реальными GUID 1С
# (сайтовый вид «Розница» 3d3bea35-5d6a-11eb-948a-f81a67046005, H-001). Без
# алиаса get_site_price возвращает None → заказ 400, price=null в Meilisearch
# (12 падений e2e в run 34358721559). Правильный фикс — helm values, но infra
# без разрешения владельца не трогаем; патч данных стенда идемпотентен: если
# helm когда-нибудь поправят на GUID, UPDATE станет no-op. До шага 8 (reindex),
# чтобы в Meilisearch ушли реальные цены.
SITE_PRICE_TYPE="$(kubectl exec deploy/promelectron-api -n "$NS" -- \
  printenv ONEC_SITE_PRICE_TYPE)" \
  || fail "не удалось прочитать ONEC_SITE_PRICE_TYPE из api"
[ -n "$SITE_PRICE_TYPE" ] || fail "ONEC_SITE_PRICE_TYPE пуст в api"
ALIASED="$(psql_query "UPDATE product_prices SET price_type='$SITE_PRICE_TYPE' WHERE price_type='3d3bea35-5d6a-11eb-948a-f81a67046005' AND price_type <> '$SITE_PRICE_TYPE' RETURNING 1" | wc -l)"
log "алиас сайтовой цены → '$SITE_PRICE_TYPE': обновлено строк product_prices: $ALIASED"

log "=== Шаг 7/10: подготовка Meilisearch ==="
# apply-путь pull-синка не ставит SEARCH_INDEX_PRODUCTS — индекс заполнит
# full reindex на шаге 8
MEILI_KEY="$(kubectl get secret promelectron-secrets -n "$NS" \
  -o jsonpath='{.data.MEILISEARCH_MASTER_KEY}' | base64 -d)"
[ -n "$MEILI_KEY" ] || fail "MEILISEARCH_MASTER_KEY пуст в promelectron-secrets"
port_forward promelectron-meilisearch 7700

log "=== Шаг 8/10: фасеты (is_filterable + full reindex) ==="
# Feature flag поиска (Redis переживает рестарты, но проверяем идемпотентно)
FLAG_ENABLED="$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" "$API/api/v1/admin/feature-flags" | python3 -c \
  "import json,sys; flags=json.load(sys.stdin); print(next((str(f['enabled']) for f in flags if f['name']=='catalog_search_meilisearch'), 'False'))")"
if [ "$FLAG_ENABLED" != "True" ]; then
  log "включаю feature flag catalog_search_meilisearch"
  curl -sf -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' -d '{"enabled": true}' \
    "$API/api/v1/admin/feature-flags/catalog_search_meilisearch" >/dev/null \
    || fail "не удалось включить catalog_search_meilisearch"
fi
# is_filterable для «Бренд»: в реальном каталоге 1С code атрибута = onec GUID (D-05),
# поэтому ищем по имени; BRAND_CODE нужен шагу 10 для проверки фасета
ATTRS_JSON="$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" "$API/api/v1/admin/attributes/")"
BRAND_ATTR="$(echo "$ATTRS_JSON" | python3 -c \
  "import json,sys; attrs=json.load(sys.stdin); a=next((x for x in attrs if x['name']=='Бренд'), None); print(f\"{a['id']} {a['code']}\" if a else '')")"
if [ -n "$BRAND_ATTR" ]; then
  BRAND_ID="${BRAND_ATTR%% *}"
  BRAND_CODE="${BRAND_ATTR##* }"
  curl -sf -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H 'Content-Type: application/json' -d '{"is_filterable": true}' \
    "$API/api/v1/admin/attributes/$BRAND_ID/" >/dev/null \
    && log "is_filterable=true: Бренд (id=$BRAND_ID, code=$BRAND_CODE)" \
    || fail "PATCH attribute Бренд не удался"
else
  fail "атрибут «Бренд» отсутствует в каталоге после синка"
fi
curl -sf -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$API/api/v1/admin/search/reindex/" >/dev/null \
  || fail "POST /admin/search/reindex/ не удался"
wait_for "job SEARCH_REINDEX_FULL completed" 360 check_reindex_done
wait_for "Meili products >= ${MIN_PRODUCTS} после reindex" 180 check_meili_docs

log "=== Шаг 9/10: загрузка реальных фото ==="
python3 "$REPO_ROOT/scripts/ci/upload_product_images.py" --api "$API" \
  || fail "upload_product_images.py: доля failed > 20%"

log "=== Шаг 10/10: верификация поиска ==="
curl -sf "$API/api/v1/search/?q=%D1%80%D0%BE%D0%B7%D0%B5%D1%82%D0%BA%D0%B0" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['total'] > 0, 'поиск «розетка»: total=0'
brand = next((f for f in d['facets'] if f['code'] == '$BRAND_CODE'), None)
assert brand and brand.get('values'), 'фасет «Бренд» пуст'
print(f\"[seed-catalog] search 'розетка': total={d['total']}, бренды={[v['value'] for v in brand['values']]}\")
" || fail "верификация поиска 'розетка' не прошла"
# «ввг» в реальном каталоге нет — проверяем по «кабель» (57 активных товаров в сиде)
curl -sf "$API/api/v1/search/suggestions/?q=%D0%BA%D0%B0%D0%B1%D0%B5%D0%BB%D1%8C" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['products'], 'suggestions «кабель» пусты'
print(f\"[seed-catalog] suggestions 'кабель': {len(d['products'])} подсказок\")
" || fail "верификация suggestions 'кабель' не прошла"
# выборочно: товар с фото (в реальном каталоге фото не у всех — берём тот, что с images)
FIRST_ID="$(psql_query "SELECT id FROM products WHERE images IS NOT NULL AND images::text != '[]' ORDER BY id LIMIT 1")"
[ -n "$FIRST_ID" ] || fail "в каталоге нет ни одного товара с фото"
# ВАЖНО: route /products/{id} БЕЗ trailing slash (иначе 307 → curl -sf даст пустое тело)
curl -sf "$API/api/v1/products/$FIRST_ID" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d.get('images'), f'у товара id={d[\"id\"]} нет images'
print(f\"[seed-catalog] товар id={d['id']} '{d['name']}': {len(d['images'])} фото\")
" || fail "верификация фото товара id=$FIRST_ID не прошла"

PRODUCTS_TOTAL="$(psql_query "SELECT count(*) FROM products")"
WITH_IMAGES="$(psql_query "SELECT count(*) FROM products WHERE images IS NOT NULL AND images::text != '[]'")"
log "=== ГОТОВО: товаров=$PRODUCTS_TOTAL, с фото=$WITH_IMAGES, окружение $NS засеяно ==="
