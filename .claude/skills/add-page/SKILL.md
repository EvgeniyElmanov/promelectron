---
name: add-page
description: Create a new React page with components, hook, API service, and tests. Delegates to frontend-dev agent.
argument-hint: "<feature/page description, e.g. 'product catalog page with filters and cart'>"
disable-model-invocation: false
context: fork
agent: frontend-dev
---

# Add React Page: $ARGUMENTS

Build the page: **$ARGUMENTS**

## Files to Create

```
frontend/src/
  pages/<Name>Page.tsx              # Route-level page component
  components/<feature>/
    <Name>Card.tsx                  # sub-components
    <Name>List.tsx
  hooks/use<Name>.ts                # data fetching + state
  services/<name>.ts                # API calls
  types/<name>.ts                   # TypeScript interfaces

frontend/src/__tests__/
  pages/<Name>Page.test.tsx
  hooks/use<Name>.test.ts
```

## Steps

1. Read an existing similar page for patterns
2. Define TypeScript types in `types/<name>.ts`
3. Create API service in `services/<name>.ts`
4. Create custom hook `use<Name>` — handles loading/error/data states
5. Build components (mobile-first TailwindCSS)
6. Build page component, wire hook + components
7. Add route in `frontend/src/App.tsx`
8. Write tests with Vitest + Testing Library (mock API calls)
9. Run `cd frontend && npm run lint && npm test`

## Rules

- Mobile-first: start without breakpoints, add `md:` only when needed
- Money display: `(amount / 100).toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' })`
- Loading state: skeleton or spinner, never blank screen
- Error state: friendly message, retry button
- Empty state: helpful message with CTA
