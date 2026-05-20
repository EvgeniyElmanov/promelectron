#!/bin/bash
set -euo pipefail

# ============================================================
# Hard Redeploy: Clean Slate for Test Environment
# Deletes EVERYTHING in namespace and recreates from scratch.
# WARNING: All test data will be lost.
# ============================================================

NAMESPACE="promelectron-test"
API_IMAGE="harbor.kubeadm.ru/promelectron/myshop-api"
FRONTEND_IMAGE="harbor.kubeadm.ru/promelectron/myshop-frontend"
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config}"

echo "=========================================="
echo "HARD REDEPLOY: Clean Slate"
echo "=========================================="

echo "=== [1/10] Cleanup runner state ==="
docker ps -q | xargs -r docker kill 2>/dev/null || true
docker container prune -f >/dev/null 2>&1 || true
docker image prune -f >/dev/null 2>&1 || true
sudo systemctl restart actions.runner.AutonomaCo-promelectron.dadeko-vm.service 2>/dev/null || true

echo "=== [2/10] Git pull latest main ==="
cd ~/AutonomaCo/actions-runner/_work/promelectron/promelectron
git fetch origin
git reset --hard origin/main
git clean -fd
COMMIT=$(git rev-parse HEAD)
echo "Commit: $COMMIT"

echo "=== [3/10] Build & push API image (no cache) ==="
docker build --no-cache -f Dockerfile.backend -t ${API_IMAGE}:${COMMIT} .
docker push ${API_IMAGE}:${COMMIT}

echo "=== [4/10] Build & push Frontend image (no cache) ==="
docker build --no-cache -f Dockerfile.frontend \
  --build-arg VITE_API_URL=https://api.promelectron-test.aidrivencode.ru \
  -t ${FRONTEND_IMAGE}:${COMMIT} .
docker push ${FRONTEND_IMAGE}:${COMMIT}

echo "=== [5/10] Hard cleanup K8s namespace ==="
kubectl delete deployment,statefulset,job,service,ingress,secret,configmap,pvc \
  --all -n ${NAMESPACE} --ignore-not-found=true
echo "Waiting for resources to terminate..."
sleep 20

echo "=== [6/10] Recreate Harbor secret ==="
kubectl create secret docker-registry harborcred \
  --docker-server=harbor.kubeadm.ru \
  --docker-username="${HARBOR_USERNAME}" \
  --docker-password="${HARBOR_PASSWORD}" \
  --namespace ${NAMESPACE} \
  --dry-run=client -o yaml | kubectl apply -f -

echo "=== [7/10] Helm install fresh ==="
helm upgrade --install promelectron-test ./infra/helm \
  --set api.image=${API_IMAGE}:${COMMIT} \
  --set frontend.image=${FRONTEND_IMAGE}:${COMMIT} \
  --namespace ${NAMESPACE} \
  --create-namespace

echo "=== [8/10] Wait for Postgres ==="
for i in $(seq 1 60); do
  READY=$(kubectl get pod -n ${NAMESPACE} -l app=myshop-postgres -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
  if [ "$READY" = "true" ]; then
    echo "✅ Postgres ready"
    break
  fi
  echo "  Waiting for postgres ($i/60)..."
  sleep 5
done

echo "=== [9/10] Run alembic migrations ==="
kubectl run migrations --rm -i --restart=Never -n ${NAMESPACE} \
  --image=${API_IMAGE}:${COMMIT} \
  --env-from=configmap/myshop-config \
  --env-from=secret/myshop-secrets \
  -- alembic upgrade head

echo "=== [10/10] Restart API/Frontend & verify ==="
kubectl rollout restart deployment/myshop-api -n ${NAMESPACE}
kubectl rollout restart deployment/myshop-frontend -n ${NAMESPACE}
kubectl rollout status deployment/myshop-api -n ${NAMESPACE} --timeout=300s
kubectl rollout status deployment/myshop-frontend -n ${NAMESPACE} --timeout=300s

echo ""
echo "=== Verification ==="
API_POD=$(kubectl get pod -n ${NAMESPACE} -l app=myshop-api -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n ${NAMESPACE} ${API_POD} -- python -c "
import sys
sys.path.insert(0, '/app')
from server.app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print('Routes found:', len(routes))
assert '/api/v1/login' in routes, 'Missing login route'
assert '/api/v1/categories' in routes, 'Missing categories route'
print('✅ API routes OK')

from server.app.db.database import SessionLocal
from server.app.models import User
db = SessionLocal()
u = db.query(User).filter(User.email == 'seed-admin@example.com').first()
print('Admin user:', 'YES' if u else 'NO — DB may be empty')
if u:
  print('Admin role:', u.role)
print('✅ DB seed OK' if u else '⚠️  DB seed MISSING')
"

echo ""
echo "=========================================="
echo "REDEPLOY COMPLETE"
echo "Frontend: https://promelectron-test.aidrivencode.ru"
echo "API:      https://api.promelectron-test.aidrivencode.ru"
echo "=========================================="
