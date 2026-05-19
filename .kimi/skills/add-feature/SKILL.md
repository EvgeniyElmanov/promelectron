---
name: add-feature
description: Add a new feature to the project following the full development cycle.
argument-hint: "<feature description>"
disable-model-invocation: false
---

# Add Feature

Add a new feature following the complete development workflow.

## Steps

### 1. Analysis
- Read relevant existing code
- Understand current architecture
- Identify affected files

### 2. Backend (if needed)
```
model → schema → service → API route → tests
```

### 3. Frontend (if needed)
```
component/page → API integration → tests
```

### 4. E2E (if UI changed)
- Test happy path
- Test error states
- Test mobile viewport

### 5. Verification
- All tests pass
- No console.log / debugger
- Ask user before commit

## Checklist

- [ ] Model created (if new entity)
- [ ] Migration created (if schema changed)
- [ ] Schema updated
- [ ] Service updated
- [ ] API endpoint added
- [ ] Frontend updated
- [ ] Tests added (backend + frontend)
- [ ] E2E tested (if UI)
- [ ] Security review passed
