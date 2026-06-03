---
name: review
description: Quick code review of current changes. Checks security, quality, and tests.
argument-hint: "[--security-only] [--quick]"
disable-model-invocation: false
---

# Review: Code Review

Perform code review on current changes.

## Modes

- Default: full review (security + quality + tests)
- `--security-only`: only security checks
- `--quick`: skip detailed analysis, focus on critical issues

## Steps

1. Get diff: `git diff`
2. Check security (if not --quick):
   - Auth guards on new endpoints
   - SQL injection risks
   - Price/stock manipulation
   - PII exposure
3. Check quality:
   - Business logic in services/
   - Type hints
   - Error handling
   - Tests present
4. Write findings to `.agent/REVIEW_FINDINGS.md` (or append to existing)

## Output Format

```markdown
# Quick Review
- **Status:** APPROVED | FIXES_NEEDED

## Security
- [x] No issues
- [ ] Issue: description

## Quality
- [x] No issues
- [ ] Issue: description

## Tests
- [x] Tests present
- [ ] Missing tests for: ...
```
