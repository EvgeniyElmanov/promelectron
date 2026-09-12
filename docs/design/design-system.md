# Пром Электрон — Design System & UI Specification

**Version:** 1.0  
**Status:** Approved  
**Project:** Пром Электрон  
**Platform:** E-commerce website  
**Primary breakpoints:** Desktop 1440px / Mobile 375px

**Approved visual mockup:** [Открыть макет главной страницы](./homepage-mockup.png)

> Детальная спецификация компонентов (кнопки, формы, состояния, размеры): [design-system-detailed.md](./design-system-detailed.md).

## 1. Purpose

Современный интернет-магазин электроники для частных покупателей и малого бизнеса.

Главная задача интерфейса: пользователь должен быстро найти нужный товар, увидеть цену и наличие и совершить покупку с минимальным количеством действий.

## 2. Design Principles

- Product first
- Simple and clear
- Modern and functional
- Minimal visual noise
- Fast to scan
- Consistent components
- Desktop + mobile as equal versions

## 3. Colors

### Primary
- `color-primary`: `#2563EB`
- `color-primary-hover`: `#1D4ED8`
- `color-primary-light`: `#EFF6FF`

### Text
- `color-text`: `#111827`
- `color-text-secondary`: `#6B7280`
- `color-text-muted`: `#9CA3AF`

### Background
- `color-background`: `#FFFFFF`
- `color-background-secondary`: `#F8FAFC`
- `color-dark`: `#111827`

### Border
- `color-border`: `#E5E7EB`

### Semantic
- `color-success`: `#16A34A`
- `color-warning`: `#F59E0B`
- `color-error`: `#DC2626`

Blue is the primary accent. Red is reserved for errors and sale states; green for positive availability/success states.

## 4. Typography

**Font:** Inter

Weights:
- 400 Regular
- 500 Medium
- 600 SemiBold
- 700 Bold

### Desktop
- Display: 48px / 700
- H1: 36px / 700
- H2: 28px / 700
- H3: 22px / 600
- Body Large: 18px / 400–500
- Body: 16px / 400
- Body Small: 14px / 400
- Caption: 12px / 400–500

### Mobile
- Display: 32px / 700
- H1: 28px / 700
- H2: 24px / 700
- H3: 20px / 600
- Body: 16px / 400
- Body Small: 14px / 400
- Caption: 12px / 400–500

## 5. Layout Grid

### Desktop
- Base width: 1440px
- Content max-width: 1200px
- 12 columns
- 24px column gap

### Tablet
- Content max-width: 960px
- 8 columns

### Mobile
- Base width: 375px
- 16px horizontal padding
- 4 columns
- 12px gap

## 6. Spacing

Use an 8-point system:

`4 / 8 / 12 / 16 / 24 / 32 / 40 / 48 / 64 / 80 / 96px`

Avoid arbitrary spacing values unless required by implementation.

## 7. Radius

- Small: 6px
- Medium: 10px
- Large: 16px
- XL: 20px
- Pill: 999px

Inputs and buttons use 10px. Product and category cards use 16px.

## 8. Shadows

Card:
`0 2px 8px rgba(15, 23, 42, 0.06)`

Card hover:
`0 8px 24px rgba(15, 23, 42, 0.10)`

Use shadows sparingly.

## 9. Components

Core reusable components:

- Header
- Mobile Header
- Navigation
- Search
- Buttons
- Inputs
- Product Card
- Category Card
- Badge
- Breadcrumbs
- Filters
- Tabs
- Pagination
- Modal
- Cart Item
- Footer

Components must use reusable Figma components/variants rather than detached copies.

## 10. Product Card

Required information:
- Product image
- Brand/name
- Price
- Old price when applicable
- Availability
- Primary CTA
- Favorite
- Optional badge

Variants:
- Default
- Hover
- Sale
- New
- Out of stock
- Added to cart
- Favorite

Desktop target: approximately 282px wide.  
Mobile: 2-column grid where appropriate.

## 11. Header

### Desktop
Main header: 72px.

Contains:
- Пром Электрон logo
- Catalog
- Search
- Phone
- Compare
- Favorites
- Account
- Cart

Category navigation is placed below the main header.

### Mobile
Separate responsive component:
- Menu
- Пром Электрон logo
- Cart
- Full-width search

Do not simply scale the desktop header.

## 12. Main Pages

### Homepage
- Header
- Category navigation
- Hero
- Benefits
- Popular categories
- Popular products
- Consultation / B2B
- Footer

### Catalog
- Breadcrumbs
- H1
- Categories
- Filters
- Sort
- Product grid
- Pagination

### Category
- Breadcrumbs
- H1
- Description
- Subcategories
- Dynamic filters
- Product grid
- Pagination

### Product
- Breadcrumbs
- Product title/SKU
- Images
- Price
- Availability
- Quantity
- Add to cart
- Buy now
- Specifications
- Description
- Delivery
- Warranty
- Reviews
- Related products

### Search
- Search field
- Query
- Result count
- Filters
- Sort
- Products
- No-results state

### Cart
- Product list
- Quantity
- Prices
- Delivery
- Total
- Checkout CTA
- Empty state

### Checkout
1. Contact information
2. Delivery method
3. Address / pickup point
4. Payment
5. Order review
6. Confirmation

## 13. Mobile Rules

Mobile is a separate layout, not a scaled desktop.

- Page padding: 16px
- CTA height: 48px
- Product grid: 2 columns where appropriate
- Filters: panel/bottom sheet
- Hero: stacked layout
- Important CTAs: full width when appropriate
- Touch targets: minimum 44px

## 14. Accessibility

- Maintain sufficient contrast
- Provide visible focus states
- Touch targets >= 44px
- Use accessible labels for icon-only actions
- Show form errors clearly
- Do not communicate important information by color alone

## 15. Figma Structure

```text
ПРОМ ЭЛЕКТРОН
├── 00 — Cover
├── 01 — Design System
├── 02 — Components
├── 03 — Desktop
│   ├── Homepage
│   ├── Catalog
│   ├── Category
│   ├── Product
│   ├── Search
│   ├── Cart
│   └── Checkout
├── 04 — Mobile
│   ├── Homepage
│   ├── Catalog
│   ├── Category
│   ├── Product
│   ├── Search
│   ├── Cart
│   └── Checkout
└── 05 — Dev
```

## 16. Development Handoff

Figma is the source of truth for visual design.

GitHub is the source of truth for implementation tasks and code.

Each GitHub development task should reference the relevant Figma frame/component.

## 17. Current Status

Approved:
- Modern Tech visual direction
- Пром Электрон logo/brand naming
- Desktop visual direction
- Design System v1.0
- Responsive approach
- Main site structure

Next:
1. Build Design System in Figma
2. Build reusable Components
3. Build Desktop pages
4. Build Mobile pages
5. Review and approve
6. Developer handoff
7. GitHub implementation tasks
8. Development
