# PLAN: gh-217 — миграции ровно в одном месте (Helm-хук) + отказ старта при расхождении схемы

## Goal

Убрать автомиграцию из lifespan приложения и заменить её явной проверкой соответствия
схемы ревизиям Alembic: при расхождении (или отсутствии `alembic_version`) старт падает
с внятной ошибкой, а единственным местом применения миграций остаётся Helm-хук
(локально — `make migrate`); успех = Must-haves спеки зелёные, `make test-backend` и
`make migrate-check` проходят.

## Steps

1. **Backend: `backend/src/app/main.py` — удалить автомиграцию (D-01).**
   - Удалить `_run_alembic_migrations`, вызов `command.upgrade` и блок
     `except Exception → logger.warning` (строки 51–57, 63–65).
   - Убрать ставшие ненужными импорты `alembic.command`, `alembic.config.Config`;
     `asyncio` и `os` оставить только если используются новой проверкой / остальным кодом
     (`os` нужен для `serve_upload` и CORS — остаётся; `asyncio` будет нужен для
     `to_thread`).
   - Проверка: `grep -rn "_run_alembic_migrations\|command.upgrade" backend/src` пуст;
     `cd backend && uv run ruff check src/` чисто (нет unused imports).

2. **Backend: `backend/src/app/main.py` — schema-version check в lifespan (D-03, D-04, D-05).**
   - Добавить приватные функции рядом с lifespan:
     - `_get_applied_revisions(conn)` — sync: `SELECT version_num FROM alembic_version`
       → `set[str]`; `ProgrammingError`/`UndefinedTable` (отсутствие таблицы) обрабатывается
       вызывающей стороной как расхождение.
     - `_check_schema_version(engine)` — async:
       1. `ScriptDirectory.from_config(Config(alembic_cfg_path)).get_heads()` через
          `asyncio.to_thread` (sync-части alembic); путь к `alembic.ini` — тот же, что был
          (`os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")`).
       2. Чтение таблицы — через `engine.connect()` + `conn.run_sync(...)`; отсутствие
          таблицы → `logger.error` + `RuntimeError` с текстом D-04 (вариант «missing table»).
       3. `set(current) != set(heads)` → `logger.error` + `RuntimeError` с текстом D-04
          (вариант mismatch, с `{current}`/`{heads}`).
   - Вызов в lifespan **до** `yield`; `engine.dispose()` остаётся после `yield`.
     Общий `except Exception` вокруг проверки **не добавлять** — любое исключение валит старт.
   - Никаких env-флагов (D-01).
   - Проверка: `cd backend && uv run ruff check src/` чисто.

3. **Backend: тесты `backend/tests/test_schema_version_check.py` (D-06).**
   - Новый файл; использовать фикстуру `test_engine` из `conftest.py` (per-test БД из
     template, схема через `create_all`, таблицы `alembic_version` в ней нет).
   - Позитив: создать таблицу `alembic_version`, вставить head-ревизию, прочитанную в самом
     тесте из `ScriptDirectory` → `_check_schema_version(test_engine)` завершается без raise.
   - Негатив 1: таблица отсутствует → `pytest.raises(RuntimeError)`.
   - Негатив 2: таблица есть, вставлена несуществующая/старая ревизия → `RuntimeError`.
   - Проверка: `cd backend && uv run pytest tests/test_schema_version_check.py -x` зелёный;
     затем полный `make -C <WORKTREE> test-backend` — весь suite зелёный (conftest не трогаем).

4. **Docs: `README.md` (D-07).**
   - В разделе локального запуска (рядом с существующей строкой `make migrate`, README.md:39)
     добавить явный пункт: перед первым стартом backend выполнить `make migrate`; без
     миграций приложение не стартует — это намеренно (проверка версии схемы на старте).
   - Проверка: визуально, текст по-русски.

5. **Docs: `PROJECT_CONTEXT.md` п.9 (D-07).**
   - Строку «Alembic миграции — при старте приложения (планируется перенос в Helm hook)»
     заменить на: миграции применяются только Helm-хуком `migrate-job.yaml`
     (`pre-install,pre-upgrade`, локально — `make migrate`); приложение на старте лишь
     проверяет соответствие `alembic_version` ↔ head-ревизиям и отказывается стартовать
     при расхождении.
   - Проверка: визуально.

6. **Финальная верификация.**
   - `make -C <WORKTREE> test-backend` — зелёный.
   - `make -C <WORKTREE> lint-backend` — ноль ошибок.
   - `make -C <WORKTREE> migrate-check` — exit 0 (миграций не добавляем, drift не появится;
     прогон обязателен по AC).
   - `grep -rn "_run_alembic_migrations\|command.upgrade" backend/src` — пуст (AC).
   - Self-review диффа: `git -C <WORKTREE> --no-pager diff origin/main...HEAD`, маппинг
     каждого Must-have на изменение; убедиться, что `infra/helm/`, `docker-compose`,
     workflows не тронуты (Out of Scope).
   - Обновить `docs/journal/session-log.md` (после зелёных прогонов).

## Risks / Open questions

- **Отсутствие таблицы `alembic_version`**: PG бросает `UndefinedTable` (обёрнут в
  `ProgrammingError`). Надёжнее ловить именно отсутствие таблицы явно
  (`SELECT to_regclass('public.alembic_version')` или try/except по SQLSTATE `42P01`),
  чтобы не перепутать с другими ошибками SQL — уточню при реализации, оба варианта
  соответствуют D-03 («отсутствие таблицы = расхождение»).
- **Путь к `alembic.ini`**: текущий код вычисляет относительно `__file__`; оставляю тот же
  подход. Если `alembic.ini` не найден — раньше миграции молча пропускались; теперь отсутствие
  конфига = исключение → отказ старта (согласуется с «не глушить», D-05).
- **Тесты**: template-БД в conftest создаётся через `create_all` и не содержит
  `alembic_version` — негативный тест «нет таблицы» получается бесплатно; позитив требует
  создания таблицы в тесте. Lifespan через `ASGITransport` не выполняется — существующий
  suite не затронут (D-06).
- **Локальный запуск без `make migrate` теперь падает** — принято владельцем; митигация —
  текст ошибки с подсказкой и пункт в README.
- **Docker-зависимость `make migrate-check`/Makefile-целей**: требуют поднятого compose;
  если окружение недоступно в sandbox — зафиксировать в отчёте как непроверенное.
