# Диаграммы последовательности бизнес-флоу Promelectron

Исходники — Mermaid (`*.mmd`), рендер — SVG (`*.svg`). Регенерация:

```bash
for f in *.mmd; do npx -y @mermaid-js/mermaid-cli -p /tmp/pptr.json -i "$f" -o "${f%.mmd}.svg"; done
```

## Диаграммы

- **catalog-1c-sync** — синхронизация каталога с 1С: **планируемый** флоу (файловый intake в MinIO → разбор → upsert в PostgreSQL → переиндексация Meilisearch → поиск с фасетами). Сейчас реализован webhook-вариант: 1С шлёт JSON-батчи на `POST /api/v1/onec/webhook/` (проверка `X-1C-Api-Key`, дедуп по batch_id/checksum, `OnecChangeLog` + job `ONEC_APPLY_CHANGES`).
- **order-checkout** — оформление заказа и оплата: `POST /api/v1/orders/create/` (проверка stock через `SELECT FOR UPDATE`, списание) → `POST /api/v1/payments/{order_id}/` → создание платежа в ЮKassa → redirect на оплату → webhook `payment.succeeded` на `/api/v1/payments/yookassa/webhook/` → заказ `paid`, ставится job `CDEK_CREATE_ORDER`.
- **cdek-delivery** — доставка CDEK после оплаты: job `CDEK_CREATE_ORDER` → создание заказа в CDEK API → трек-номер → webhook-статусы (`POST /api/v1/cdek/webhooks/cdek/`) + polling через job `CDEK_SYNC_ORDER_STATUS` → обновление статуса заказа → уведомление покупателя (NotificationService + WebSocket `/ws/notifications`).
- **order-cancel-refund** — отмена заказа админом (`POST /api/v1/admin/orders/{order_id}/cancel/`): строгий refund в ЮKassa для оплаченных (при сбое — 502, заказ не отменяется) → возврат stock → best-effort отмена в CDEK. Альтернатива: отмена неоплаченного платежа пользователем (`POST /api/v1/payments/{payment_id}/cancel/`).
- **guest-cart-merge** — гостевая корзина на клиенте и merge в серверную корзину после входа: `POST /api/v1/cart/merge` (проверка stock, суммирование количеств).

## Замечания

- Meilisearch в коде бэкенда пока отсутствует — поиск реализован SQL-запросами (`GET /api/v1/products/`); интеграция поискового движка — план.
- Файлового intake с MinIO в коде нет; `POST /api/v1/onec/intake/` не существует — реализован JSON-webhook `/api/v1/onec/webhook/`.
