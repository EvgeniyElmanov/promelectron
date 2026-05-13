#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Остановка dev-окружения My Shop..."

BACKEND_PID_FILE="/tmp/myshop_backend.pid"
FRONTEND_PID_FILE="/tmp/myshop_frontend.pid"

if [[ -f "$BACKEND_PID_FILE" ]]; then
    PID=$(cat "$BACKEND_PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "  Останавливаем backend (pid $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$BACKEND_PID_FILE"
fi

if [[ -f "$FRONTEND_PID_FILE" ]]; then
    PID=$(cat "$FRONTEND_PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "  Останавливаем frontend (pid $PID)..."
        kill "$PID" 2>/dev/null || true
        sleep 1
        kill -9 "$PID" 2>/dev/null || true
    fi
    rm -f "$FRONTEND_PID_FILE"
fi

# Fallback: убиваем по именам процессов
pkill -f "uvicorn server.app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

echo "✅ Dev-окружение остановлено."
