---
description: Backend testing conventions — as they actually are in this codebase.
paths:
  - "backend/tests/**/*.py"
  - "backend/src/app/**/*.py"
---

# Testing Conventions

> Тесты живут в `backend/tests/`, код — в `backend/src/app/`.

## Раскладка

**Плоская, не зеркальная.** 41 файл вида `backend/tests/test_<область>.py`
(`test_orders.py`, `test_payments.py`, `test_auth.py`). Каталога `tests/services/` нет и
заводить его не надо — новый тест кладётся в файл своей области.

## Запуск

```bash
make test-backend      # pytest в docker-compose (postgres + redis)
make test-frontend     # vitest
make test-e2e          # Playwright, поднимает весь стек
make pre-push          # lint + unit + e2e — перед push
```

⚠️ `make test-backend` и `make test-onec-mock` сериализованы через `flock`
(`TEST_BACKEND_LOCK`): параллельные прогоны дрались за template-БД и давали сотни ложных
ошибок (LESSONS_LEARNED 2026-08-01). Вторая сессия **ждёт**, а не падает — это нормально.

## Как писать

- БД настоящая, поднимается docker-compose; **слой БД не мокается**. Фикстуры — в
  `backend/tests/conftest.py`, клиент — `httpx.AsyncClient` поверх `ASGITransport`.
- Внешний HTTP мокается через `respx` (см. `conftest.py`, `test_auth.py`).
- Имя теста говорит, что проверяется: `test_cancel_paid_order`, а не `test_order_2`.
- Побочные эффекты убираются за собой — фикстурой или откатом транзакции.
- В разработке `pytest -x` (падать сразу), перед коммитом — полный прогон.

## Чего тесты не ловят сами

Зелёные тесты **не** доказывают, что фича работает: в этом проекте уже дважды случалось, что
смерженная фича молча откатывалась коммитом из устаревшего working tree, а тесты оставались
зелёными. Отдельно проверяй:

- **проверка мутацией** для гейтов и линтеров — внеси нарушение, дождись красного, убери,
  дождись зелёного. Без этого «гейт работает» — предположение;
- **вызывается ли новый код на живом пути** — модуль, покрытый юнит-тестами и никем не
  вызываемый, даёт ложную уверенность;
- **изоляция E2E-кейсов** — состояние корзины, пользователя и каталога не должно протекать
  между тестами (issue #186 — ровно этот класс).
