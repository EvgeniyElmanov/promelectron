---
name: sync-onec
description: Trigger a manual 1C product sync and monitor the result.
disable-model-invocation: true
allowed-tools: Bash(cd *) Bash(psql *) Bash(curl *) Bash(kubectl *)
---

# Manual 1C Product Sync

1C sync now runs through the `job_worker` and the `jobs` table (`ONEC_FULL_SYNC` / `ONEC_APPLY_CHANGES`).

## Check for an active sync

```bash
psql "$DATABASE_URL" -c "SELECT id, status, job_type, attempts, created_at FROM jobs WHERE job_type = 'ONEC_FULL_SYNC' AND status IN ('pending', 'running') ORDER BY created_at DESC LIMIT 5;"
```

Or check the job-worker logs:

```bash
kubectl logs -l app=promelectron-job-worker -f --tail=50
```

## Steps

1. If an `ONEC_FULL_SYNC` job is already pending or running — report it and stop.
2. If not running, trigger a full sync via the admin endpoint:
   ```bash
   curl -X POST "$API_BASE_URL/api/v1/admin/onec/full-sync/" \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```
   Or enqueue directly in the database:
   ```bash
   psql "$DATABASE_URL" -c "INSERT INTO jobs (job_type, payload, status) VALUES ('ONEC_FULL_SYNC', '{}', 'pending');"
   ```
3. Monitor the `promelectron-job-worker` logs for progress.
4. Report: products synced count, errors, duration.

## Troubleshooting

| Symptom | Check | Fix |
|---------|-------|-----|
| Auth error | Job-worker logs `OnecAuthError` | Rotate `ONEC_API_KEY` / `ONEC_PASSWORD` in K8s secret |
| Connection error | Job-worker logs `OnecConnectionError` | Check `ONEC_API_URL` and network |
| Sync not running | Job-worker pod status / logs | Ensure `promelectron-job-worker` deployment has replicas > 0 |
| Slow sync (>5 min) | Job-worker logs with timing | Check 1C API response times |
