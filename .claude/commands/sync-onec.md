# Manual 1C Product Sync

Check if a sync is already running:

```!
cd backend && uv run celery -A app.workers.celery_app inspect active 2>&1 || echo "Celery not reachable locally — check kubectl"
```

## Steps

1. If a sync is already running — report it and stop
2. If not running, trigger manually:
   ```bash
   cd backend && uv run celery -A app.workers.celery_app call app.workers.tasks.sync_products_from_onec
   ```
3. Monitor Celery worker logs for the task result
4. Report: products synced count, errors, duration

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Auth error | Worker logs `OnecAuthError` | Rotate `ONEC_API_KEY` in K8s secret |
| Connection error | Worker logs `OnecConnectionError` | Check `ONEC_API_URL` and network |
| Task not running | Beat logs | Ensure celery-beat pod is running (replica=1) |
| Slow sync (>5 min) | Worker logs with timing | Check 1C API response times |
