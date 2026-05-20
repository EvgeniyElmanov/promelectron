#!/bin/sh
set -e

echo "Seeding test data..."
python seed_data.py || echo "Seed skipped (may already exist)"

echo "Starting application..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8000
