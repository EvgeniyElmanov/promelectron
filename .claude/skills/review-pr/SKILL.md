---
name: review-pr
description: Comprehensive pull request review covering correctness, security, architecture, tests, and database safety.
disable-model-invocation: true
allowed-tools: Read Bash(git diff *) Bash(git log *) Bash(git status *) Bash(cd *) Grep Glob
---

# Pull Request Review

## Current Branch

```!
git log main..HEAD --oneline
git diff main...HEAD --stat
```

## Review Checklist

Run `git diff main...HEAD` and check every changed file against this:

### Correctness
- [ ] Code does what the commit messages claim
- [ ] Edge cases handled: empty collections, null values, concurrent requests
- [ ] Error paths return meaningful error responses

### Security (e-commerce specific)
- [ ] No secrets or credentials hardcoded
- [ ] Auth check on every protected endpoint
- [ ] Object-level auth: user can only access their own orders/cart
- [ ] Payment webhook signature verified before processing
- [ ] Amounts calculated server-side — never trusted from client
- [ ] No SQL injection vectors (raw query strings?)

### Architecture
- [ ] Business logic in `services/` — not in route handlers or models
- [ ] Integrations accessed via `service.py` — not `client.py` directly
- [ ] No circular imports

### Database
- [ ] Migration created for model changes?
- [ ] Soft-delete used instead of hard-delete for user/order data?
- [ ] Money stored as integers (kopecks)?
- [ ] Indexes added for new WHERE/ORDER BY columns?
- [ ] No N+1 query patterns?

### Tests
- [ ] Tests added for new behaviour?
- [ ] Failure cases covered, not just happy path?
- [ ] No mocked DB sessions in backend tests?
- [ ] External HTTP calls mocked with respx?

## Output Format

```
## Summary
<2-3 sentences on what this PR does>

## Issues

### Critical (block merge)
- file:line — description

### Warning (should fix)
- file:line — description

### Suggestion (nice to have)
- file:line — description

## Verdict
APPROVE | REQUEST CHANGES | NEEDS DISCUSSION
```
