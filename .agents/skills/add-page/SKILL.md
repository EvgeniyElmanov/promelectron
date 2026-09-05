---
name: add-page
description: Create a new Vue 3 page with components, composable, API service, and tests. Delegates to frontend-dev agent.
argument-hint: "<feature/page description, e.g. 'product catalog page with filters and cart'>"
disable-model-invocation: false
context: fork
agent: frontend-dev
---

# Add Vue Page: $ARGUMENTS

Build the page: **$ARGUMENTS**

## Files to Create

```
frontend/src/
  views/<Name>View.vue              # Route-level page component
  components/<feature>/
    <Name>Card.vue                  # sub-components
    <Name>List.vue
  composables/use<Name>.js          # data fetching + state
  services/<name>.js                # API calls

frontend/src/__tests__/
  views/<Name>View.spec.js
  composables/use<Name>.spec.js
```

## Steps

1. Read an existing similar view for patterns
2. Create API service in `services/<name>.js`
3. Create custom composable `use<Name>` — handles loading/error/data states
4. Build components
5. Build view component, wire composable + components
6. Add route in `frontend/src/router/index.js`
7. Write tests with Vitest + Vue Test Utils (mock API calls)
8. Run `cd frontend && npm run lint && npm test`

## Rules

- Money display: `(amount / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' })
- Loading state: skeleton or spinner, never blank screen
- Error state: friendly message, retry button
- Empty state: helpful message with CTA
