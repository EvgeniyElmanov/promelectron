---
name: web-conventions
description: Vue 3 frontend conventions for Promelectron — component structure, API integration, composables, and views.
when_to_use: Load when implementing or reviewing any Vue 3 frontend code in frontend/.
user-invocable: false
paths:
  - "frontend/**/*.vue"
  - "frontend/**/*.js"
  - "frontend/**/*.css"
---

# Web Frontend Conventions — Promelectron

## Stack

- Vue 3 + Vite + JavaScript
- Vue Router for navigation
- Axios for API calls
- Vitest + Vue Test Utils for unit/component tests

## Structure

```
frontend/src/
  views/          # Route-level page components
  components/     # Reusable UI components
  composables/    # Custom Vue composables
  services/       # API client functions
  utils/          # Pure utility functions
```

## Rules

- API calls only in `services/` — not directly in components
- Custom composables for all data fetching: `useProducts()`, `useCart()`, etc.
- API calls only in `services/` — not directly in components
- Money: receive `int` (kopecks) from API, display with `/ 100` and `toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' })`
- All user-facing strings in Russian — no hardcoded English in UI
- Forms: controlled components with validation before submit
- Error states: always show user-friendly message, never raw API errors

## API Integration

```javascript
// services/products.js
import axios from './client';
export const getProducts = (page = 1) =>
  axios.get('/api/v1/products', { params: { page, limit: 20 } });
```

API base URL from `import.meta.env.VITE_API_URL` or relative `/api/v1`.
