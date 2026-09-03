---
description: External integration conventions — as they actually are in this codebase.
paths:
  - "backend/src/app/services/*_client.py"
  - "backend/src/app/services/*_service.py"
  - "backend/src/app/api/onec.py"
  - "backend/src/app/api/cdek.py"
  - "backend/src/app/api/payments.py"
---

# Integration Conventions

> ⚠️ Каталога `backend/app/integrations/` **не существует**. Интеграции живут в
> `backend/src/app/services/` парами «клиент + сервис». `backend/src/integrations/collector/` —
> это отдельный проект со своим `pyproject.toml`, к интеграциям приложения отношения не имеет.

## Как здесь на самом деле

| Интеграция | Клиент | Сервис | Эндпоинты |
|---|---|---|---|
| СДЭК | `cdek_client.py` | `cdek_service.py` | `api/cdek.py` + два CronJob |
| ЮKassa | — (SDK) | `yookassa_service.py`, `payment_service.py` | `api/payments.py` |
| 1С | — (вход по webhook) | `onec_intake_service.py`, `onec_sync_service.py`, `onec_webhook_service.py`, `onec_intake_loader.py` | `api/onec.py` |
| Meilisearch | — | `search_indexing.py`, `search_query.py` | за feature-флагом |

- **Клиент** знает про HTTP, авторизацию, ретраи и формат внешней системы.
- **Сервис** — то, что импортирует остальное приложение. Клиент напрямую из бизнес-логики
  не вызывается.
- Ошибки внешней системы заворачиваются в доменные исключения (`CdekAPIError` и т.п.), а не
  протекают наружу как `httpx`-ошибки.

## Обязательное

- **1С — только на чтение.** В 1С писать нельзя. Приём — `POST /onec/intake/` с проверкой
  `X-1C-Checksum` (#162); полная синхронизация — админским эндпоинтом или webhook'ом,
  обработка — через `job_worker` (таблица `jobs`).
- **Вебхуки платежей проверяются по подписи ДО обработки.** Сейчас в
  `payment_service.py:417` проверка условная: без заголовка подписи она пропускается и
  обработка продолжается. Это дыра, а не образец — новый код так писать нельзя, а сумму из
  вебхука надо сверять с суммой платежа в БД.
- **Тестовые контуры не протекают в прод.** `CDEK_API_URL` по умолчанию `api.edu.cdek.ru`,
  `CDEK_TEST_MODE=true` — prod обязан переопределять оба. Debug-эндпоинты платежей
  (`/payments/debug/*`) закрыты только флагом `YOOKASSA_TEST_MODE`.
- Новая интеграция начинается с задачи в бэклоге и решения владельца: это вопрос денег и
  безопасности, агент его не принимает.
