---
name: known-pitfalls
description: >
  Real pitfalls that have already happened in Promelectron. Check before committing.
type: prompt
disableModelInvocation: true
---

# Known pitfalls (Promelectron)

> Real issues that have already happened. Check before committing.

## 1. Tests must not touch dev/prod DB

`conftest.py` uses a separate test database. Always run `make test-backend` (PostgreSQL in Docker), never `pytest` locally on SQLite.

## 2. Rate limiting breaks tests

Reset the limiter in the `client` fixture.

## 3. SQLite ≠ PostgreSQL

Foreign keys, unique constraints, and SQL syntax differ. Test against PostgreSQL.

## 4. Trailing slash in FastAPI

`api.get('/categories/')` matches `@router.get("/")`. Missing trailing slash causes 307/CORS issues.

## 5. Docker `node_modules` permissions

After `npm install` in a container, fix ownership with `sudo chown -R $(whoami):$(whoami) frontend/node_modules`.

## 6. `docker-entrypoint.sh` executable bit

Run `chmod +x backend/docker-entrypoint.sh` before starting.

## 7. `docker-entrypoint.sh` ignores arguments

Use `--entrypoint ""` for one-off commands: `docker compose run --rm --entrypoint "" api alembic upgrade head`.

## 8. Vite proxy hostname in Docker

Use service name: `proxy: { '/api': { target: 'http://api:8000', changeOrigin: true } }`.

## 9. Alembic version without tables

If `drop_all` removed tables but `alembic_version` remains, run `DELETE FROM alembic_version;` then `alembic upgrade head`.

## 10. Duplicate route without guard

Keep only one route definition with the correct `meta` guards.

## 11. Path traversal in filename

Sanitize filenames with `os.path.basename` and `os.path.realpath` checks.
