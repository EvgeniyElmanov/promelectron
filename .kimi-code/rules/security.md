---
name: security
description: >
  Security checklist for Promelectron agents.
type: prompt
disableModelInvocation: true
---

## Rule: security

> **Правило:** Применяй этот чеклист к каждому изменению кода, особенно если задача касается auth, payments, загрузки файлов, внешних интеграций или PII.
> При русскоязычном пользователе пиши findings и отчёты на русском.
> См. [Rule: Agent Commons](agent-commons.md) > Языковое правило.

### API Endpoints

- [ ] **Auth guard**: Все непубличные endpoint'ы используют `Depends(get_current_user)` / `Depends(get_current_active_admin)` / `Depends(get_current_active_supplier)`
- [ ] **Object ownership**: Пользователь может обращаться только к своим данным (orders, cart, profile, recipients)
- [ ] **Admin guard**: Admin endpoint'ы проверяют роль через схему ролей проекта, не хардкод строку `"admin"`
- [ ] **Input validation**: Все входные данные валидируются через Pydantic-схемы
- [ ] **Rate limiting**: Чувствительные endpoint'ы (login, register, password-reset) защищены лимитами
- [ ] **Trailing slash**: Endpoint'ы используют trailing slash (см. [Rule: Known Pitfalls](known-pitfalls.md))

### База данных

- [ ] **No raw SQL with f-strings**: Используй ORM-запросы. Если raw SQL необходим — только `text()` с bind-параметрами
- [ ] **Migration safety**: Миграции не удаляют данные без явного `op.execute` и backup
- [ ] **SELECT FOR UPDATE**: Для критичных операций со stock и платежами

### Бизнес-логика

- [ ] **Price from DB**: Итоговая сумма заказа считается из цен в БД, клиент не доверяется
- [ ] **Stock check**: Уменьшение stock атомарно, с проверкой до decrement
- [ ] **Idempotency**: Платёжные endpoint'ы идемпотентны (idempotency key / уникальность external_id)
- [ ] **Coupon validation**: Проверка срока, лимитов использования, применимости
- [ ] **State machine**: Статусы заказа/платежа меняются допустимыми переходами
- [ ] **Money-movement audit**: Любой admin endpoint, инициирующий движение денег (refund / payout), обязан фиксировать actor (`current_user.id`) в audit-логе — без PII (только id, action, сумма, заказ)

### Фронтенд

- [ ] **No secrets in code**: API keys, tokens не захардкожены
- [ ] **JWT storage**: Текущий проект использует localStorage (известный риск, планируется HttpOnly cookies + refresh tokens)
- [ ] **XSS prevention**: `v-html` используется только с доверенным HTML
- [ ] **CSRF**: Stateless Bearer; для OAuth callback обязателен `state` параметр

### Логирование

- [ ] **No PII in logs**: Не логировать emails, passwords, card numbers, phone
- [ ] **No tokens in logs**: Не логировать JWT, OAuth tokens, API keys
- [ ] **Secure fallback**: При ошибках SMTP/платежей не утекать секреты в traceback

### Project-specific риски (из AUDIT.md)

- [ ] **Hardcoded secrets**: Нет default `SECRET_KEY`, `SEED_SECRET`, тестовых паролей в коде
- [ ] **Containers as root**: Docker-образы запускаются от non-root пользователя
- [ ] **Auto-seed in prod**: `seed_data.py` не запускается автоматически в production
- [ ] **Distributed rate limiting**: Rate limiting работает через Redis, а не in-memory
- [ ] **NetworkPolicies**: В Helm есть NetworkPolicies для изоляции БД/Redis/MinIO
- [ ] **File uploads**: Проверка MIME-type, размера, расширения; защита от path traversal
- [ ] **Webhook signatures**: YooKassa/CDEK webhooks верифицируются по подписи
- [ ] **SSRF**: Внешние HTTP-вызовы через allow-list / валидацию URL

### DevOps / Infra

- [ ] **Secrets management**: Секреты только в GitHub Secrets / SOPS, никакого plaintext
- [ ] **CI/CD gate**: `make pre-push` (lint + tests + E2E) проходит перед deploy
- [ ] **Image scanning**: Образы сканируются на CVE
- [ ] **Non-root containers**: `securityContext.runAsNonRoot: true`, `readOnlyRootFilesystem`
- [ ] **HTTPS**: Production endpoint'ы только `https://`, HSTS

### Формат security findings

Если находишь проблему, оформляй в формате:

```markdown
### [S-001] 🔴 CRITICAL | <Category>
- **File:** path/to/file.py:42
- **Evidence:** <цитата/фрагмент из diff>
- **Problem:** ...
- **Impact:** <security риск и blast radius>
- **Action:** <конкретное исправление>
- **Status:** OPEN
```

Severity: 🔴 CRITICAL / 🟠 HIGH / 🟡 MEDIUM / 🟢 LOW.

---
