#!/bin/sh
set -e

echo "Starting application..."
exec uvicorn server.app.main:app --host 0.0.0.0 --port 8000
