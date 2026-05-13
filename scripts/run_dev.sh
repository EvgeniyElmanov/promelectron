#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID_FILE="/tmp/myshop_backend.pid"
FRONTEND_PID_FILE="/tmp/myshop_frontend.pid"

echo "🚀 Запуск dev-окружения My Shop..."

# Проверка занятости портов
if lsof -i :8000 >/dev/null 2>&1; then
    echo "⚠️  Порт 8000 занят. Останавливаем старый процесс..."
    lsof -ti :8000 | xargs kill -9 2>/dev/null || true
fi

if lsof -i :5173 >/dev/null 2>&1; then
    echo "⚠️  Порт 5173 занят. Останавливаем старый процесс..."
    lsof -ti :5173 | xargs kill -9 2>/dev/null || true
fi

# Запуск backend
echo "🔧 Запуск backend (uvicorn :8000)..."
cd "$PROJECT_ROOT"
source venv/bin/activate
uvicorn server.app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/myshop_backend.log 2>&1 &
echo $! > "$BACKEND_PID_FILE"

# Запуск frontend
echo "🎨 Запуск frontend (vite :5173)..."
cd "$PROJECT_ROOT/client"
npm run dev > /tmp/myshop_frontend.log 2>&1 &
echo $! > "$FRONTEND_PID_FILE"

# Ожидание старта
echo "⏳ Ожидание запуска сервисов..."
for i in {1..30}; do
    BACKEND_READY=false
    FRONTEND_READY=false

    if curl -s http://localhost:8000/ >/dev/null 2>&1; then
        BACKEND_READY=true
    fi

    if curl -s http://localhost:5173 >/dev/null 2>&1; then
        FRONTEND_READY=true
    fi

    if [[ "$BACKEND_READY" == "true" && "$FRONTEND_READY" == "true" ]]; then
        echo "✅ Dev-окружение готово!"
        echo "   Backend:  http://localhost:8000"
        echo "   Frontend: http://localhost:5173"
        echo "   Logs:     /tmp/myshop_backend.log /tmp/myshop_frontend.log"
        exit 0
    fi

    sleep 1
done

echo "❌ Таймаут ожидания запуска сервисов. Проверь логи:"
echo "   Backend:  tail -n 20 /tmp/myshop_backend.log"
echo "   Frontend: tail -n 20 /tmp/myshop_frontend.log"
exit 1
