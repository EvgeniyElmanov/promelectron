---
name: security-check
description: Run security audit on current changes. Checks auth, injection, data exposure, business logic vulnerabilities.
argument-hint: ""
disable-model-invocation: false
---

# Security Check

Run security audit on current code changes.

## Checks

### Authentication
- [ ] All new endpoints have auth guards
- [ ] Admin endpoints check admin role
- [ ] Users can only access their own data

### Injection
- [ ] No raw SQL with string formatting
- [ ] All inputs validated via Pydantic
- [ ] No command injection

### Data Exposure
- [ ] No PII in logs
- [ ] No passwords/tokens in API responses
- [ ] No debug endpoints

### Business Logic
- [ ] Prices from DB, not client
- [ ] Stock checked atomically
- [ ] Cart quantities validated (positive)
- [ ] Order totals calculated server-side

## Output

```markdown
# Security Audit
- **Status:** PASSED | ISSUES_FOUND

## Issues

### [S001] 🔴 CRITICAL | <Type>
**File:** `path:line`
**Problem:** description
**Fix:** how to fix
```
