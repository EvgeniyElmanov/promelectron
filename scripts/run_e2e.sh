#!/usr/bin/env bash
#
# run_e2e.sh — Запуск бэкенда + фронтенда для e2e тестов
# Используется агентом tester
#
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo "🛑 Останавливаю сервера..."
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
    [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
    pkill -f "uvicorn server.app.main" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    echo "✅ Сервера остановлены"
}

trap cleanup EXIT

echo "🚀 Запускаю бэкенд..."
cd "$PROJECT_DIR"
source venv/bin/activate
uvicorn server.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "   PID=$BACKEND_PID"

echo "🚀 Запускаю фронтенд..."
cd "$PROJECT_DIR/client"
npm run dev &
FRONTEND_PID=$!
echo "   PID=$FRONTEND_PID"

echo "⏳ Жду 5 секунд пока сервера стартуют..."
sleep 5

echo "✅ Бэкенд: http://localhost:8000"
echo "✅ Фронтенд: http://localhost:5173"
echo ""
echo "Сервера запущены. Можешь подключаться Playwright MCP к http://localhost:5173"
echo "Для остановки нажми Ctrl+C"

# Держим скрипт живым пока работает тестирование
wait
