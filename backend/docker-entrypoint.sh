#!/bin/sh
set -e

echo "Starting application..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
