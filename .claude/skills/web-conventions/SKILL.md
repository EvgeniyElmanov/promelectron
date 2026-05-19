---
name: web-conventions
description: React web frontend conventions for Promelectron — component structure, TailwindCSS, API integration, mobile-first design.
when_to_use: Load when implementing or reviewing any React frontend code in frontend/.
user-invocable: false
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
  - "frontend/**/*.css"
---

# Web Frontend Conventions — Promelectron

## Stack

- React 19 + Vite + TypeScript
- TailwindCSS — **mobile-first** (start with mobile, add `md:` / `lg:` breakpoints)
- React Router v6 for navigation
- Axios for API calls
- Vitest + Testing Library for unit/component tests

## Structure

```
frontend/src/
  pages/          # Route-level page components
  components/     # Reusable UI components
  hooks/          # Custom React hooks
  services/       # API client functions
  types/          # TypeScript interfaces
  utils/          # Pure utility functions
```

## Rules

- **Mobile-first**: default styles for mobile, `md:`/`lg:` for larger screens
- No class-based components — functional components only
- Custom hooks for all data fetching: `useProducts()`, `useCart()`, etc.
- API calls only in `services/` — not directly in components
- Money: receive `int` (kopecks) from API, display with `/ 100` and `toLocaleString('ru-RU', { style: 'currency', currency: 'RUB' })`
- All user-facing strings in Russian — no hardcoded English in UI
- Forms: controlled components with validation before submit
- Error states: always show user-friendly message, never raw API errors

## API Integration

```typescript
// services/products.ts
import axios from './client';
export const getProducts = (page = 1) =>
  axios.get('/api/v1/products', { params: { page, limit: 20 } });
```

API base URL from `import.meta.env.VITE_API_URL`.
