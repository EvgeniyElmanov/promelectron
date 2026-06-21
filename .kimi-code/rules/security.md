---
name: promelectron.rules.security
description: >
  Security checklist for Promelectron agents.
type: prompt
disableModelInvocation: true
---

## Rule: security

Apply this checklist to every code change.

### API Endpoints

- [ ] **Auth guard**: All non-public endpoints use `Depends(get_current_user)` or `Depends(get_current_active_admin)`
- [ ] **Object ownership**: Users can only access their own data (orders, cart, profile)
- [ ] **Admin guard**: Admin endpoints check `role == "admin"`
- [ ] **Input validation**: All inputs validated via Pydantic schemas

### Database

- [ ] **No raw SQL**: Use ORM queries, never `text("SELECT * FROM ...")` with f-strings
- [ ] **Parameterized queries**: If raw SQL needed — use bind parameters
- [ ] **Migration safety**: Migrations don't drop data unexpectedly

### Business Logic

- [ ] **Price from DB**: Order total calculated from DB prices, never trust client
- [ ] **Stock check**: Decrement stock atomically, check before decrement
- [ ] **Idempotency**: Payment endpoints use idempotency keys
- [ ] **Coupon validation**: Check expiration, usage limits, applicability

### Frontend

- [ ] **No secrets in code**: API keys, tokens not hardcoded
- [ ] **XSS prevention**: Don't use `v-html` with user input
- [ ] **CSRF**: API uses Bearer tokens (stateless), no cookie-based auth

### Logging

- [ ] **No PII in logs**: Don't log emails, passwords, card numbers
- [ ] **No tokens in logs**: Don't log JWT tokens

---

