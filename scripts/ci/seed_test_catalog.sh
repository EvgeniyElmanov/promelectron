#!/usr/bin/env bash
# CI-оркестратор сидинга каталога электротоваров на test-стенде (issue #147).
#
# Цепочка: cleanup → reseed users/supplier → restart api+onec-mock → seed мока
# (30 SKU) → /trigger/ → intake → ONEC_INTAKE_PROCESS → SEARCH_INDEX_PRODUCTS →
# Meilisearch → фасеты (is_filterable + full reindex) → реальные фото → верификация поиска.
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
# F004: значение читаем из кластера (onecMock.seedProductsCount → env деплоя),
# fallback 30 при недоступности (например, до первого деплоя значения).
EXPECTED_PRODUCTS="$(kubectl get deploy promelectron-onec-mock -n "$NS" \
  -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="SEED_PRODUCTS_COUNT")].value}' \
  2>/dev/null || true)"
EXPECTED_PRODUCTS="${EXPECTED_PRODUCTS:-30}"
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
  curl -sf "http://localhost:8100/status/" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d['catalog']['products'] >= ${EXPECTED_PRODUCTS} else 1)" \
    2>/dev/null
}

check_intake_parsed() {
  [ "$(psql_query "SELECT status FROM onec_intake_log ORDER BY id DESC LIMIT 1" 2>/dev/null)" = "parsed" ]
}

check_index_job_done() {
  [ "$(psql_query "SELECT count(*) FROM jobs WHERE job_type='SEARCH_INDEX_PRODUCTS' AND status='completed'" 2>/dev/null)" -ge 1 ] 2>/dev/null
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

log "=== Шаг 3/10: rollout restart api + onec-mock ==="
# api — стирает local uploads (emptyDir); мок — пересоздаёт схему onec_mock и сеет каталог
kubectl rollout restart deployment/promelectron-api deployment/promelectron-onec-mock -n "$NS"
kubectl rollout status deployment/promelectron-api -n "$NS" --timeout=180s \
  || fail "api не поднялся после restart"
kubectl rollout status deployment/promelectron-onec-mock -n "$NS" --timeout=180s \
  || fail "onec-mock не поднялся после restart"

log "=== Шаг 4/10: ожидание seed мока (>= ${EXPECTED_PRODUCTS} SKU) ==="
port_forward promelectron-onec-mock 8100
wait_for "мок посеял каталог" 120 check_mock_seeded

log "=== Шаг 5/10: триггер отправки каталога ==="
TRIGGER_OUT="$(curl -sf -X POST http://localhost:8100/trigger/)" \
  || fail "POST /trigger/ мока не удался"
echo "$TRIGGER_OUT" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(f'[seed-catalog] trigger: {d}'); sys.exit(0 if d.get('status') == 'success' else 1)" \
  || fail "trigger вернул не success: $TRIGGER_OUT"

log "=== Шаг 6/10: ожидание парсинга intake (timeout 360s) ==="
wait_for "onec_intake_log.status='parsed'" 360 check_intake_parsed

log "=== Шаг 7/10: ожидание индексации Meilisearch ==="
wait_for "job SEARCH_INDEX_PRODUCTS completed" 360 check_index_job_done
MEILI_KEY="$(kubectl get secret promelectron-secrets -n "$NS" \
  -o jsonpath='{.data.MEILISEARCH_MASTER_KEY}' | base64 -d)"
[ -n "$MEILI_KEY" ] || fail "MEILISEARCH_MASTER_KEY пуст в promelectron-secrets"
port_forward promelectron-meilisearch 7700
wait_for "Meili products >= ${MIN_PRODUCTS} документов" 180 check_meili_docs

log "=== Шаг 8/10: фасеты (is_filterable + full reindex) ==="
ADMIN_TOKEN="$(api_login "$ADMIN_EMAIL" "$ADMIN_PASSWORD")" \
  || fail "login seed-admin не удался"
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
# is_filterable для ключевых атрибутов (только существующие коды)
FILTERABLE_CODES="brand color rated_current_a wire_cross_section_mm2 ip_rating"
ATTRS_JSON="$(curl -sf -H "Authorization: Bearer $ADMIN_TOKEN" "$API/api/v1/admin/attributes/")"
for code in $FILTERABLE_CODES; do
  ATTR_ID="$(echo "$ATTRS_JSON" | python3 -c \
    "import json,sys; attrs=json.load(sys.stdin); print(next((a['id'] for a in attrs if a['code']=='$code'), ''))")"
  if [ -n "$ATTR_ID" ]; then
    curl -sf -X PATCH -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H 'Content-Type: application/json' -d '{"is_filterable": true}' \
      "$API/api/v1/admin/attributes/$ATTR_ID/" >/dev/null \
      && log "is_filterable=true: $code (id=$ATTR_ID)" \
      || fail "PATCH attribute $code не удался"
  else
    log "атрибут $code отсутствует в каталоге — пропуск"
  fi
done
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
brand = next((f for f in d['facets'] if f['code'] == 'brand'), None)
assert brand and brand.get('values'), 'фасет brand пуст'
print(f\"[seed-catalog] search 'розетка': total={d['total']}, бренды={[v['value'] for v in brand['values']]}\")
" || fail "верификация поиска 'розетка' не прошла"
curl -sf "$API/api/v1/search/suggestions/?q=%D0%B2%D0%B2%D0%B3" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert d['products'], 'suggestions «ввг» пусты'
print(f\"[seed-catalog] suggestions 'ввг': {len(d['products'])} подсказок\")
" || fail "верификация suggestions 'ввг' не прошла"
# выборочно: у первого товара есть фото
FIRST_ID="$(curl -sf "$API/api/v1/products/?limit=1" | python3 -c \
  "import json,sys; print(json.load(sys.stdin)['items'][0]['id'])")"
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
