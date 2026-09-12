# Пром Электрон — Design System & UI Specification (детальная)

> **Примечание:** это исходная детальная версия спеки, написанная под рабочим названием
> «Modern Tech». Проект — **Пром Электрон**; все упоминания Modern Tech внутри читать как
> Пром Электрон. Краткая (обзорная) версия — [design-system.md](./design-system.md).

**Version:** 1.0  
**Status:** Approved  
**Project:** Пром Электрон (исходное рабочее название: Modern Tech)  
**Platform:** E-commerce website  
**Primary breakpoints:** Desktop 1440px / Mobile 375px

---

## 1. Purpose

Modern Tech — современный интернет-магазин электроники и сопутствующих товаров.

Основная задача интерфейса:

> Пользователь должен быстро понять, что продаётся, найти нужный товар, увидеть цену и наличие и совершить покупку с минимальным количеством действий.

Design principles:

- Simple
- Clear
- Modern
- Functional
- Product-focused
- Fast to scan
- Consistent
- Mobile-first in interaction logic

---

# 2. Design Principles

### 2.1. Product first

Главный объект интерфейса — товар.

Приоритет информации:

1. Product
2. Product name
3. Price
4. Availability
5. Primary CTA
6. Additional information

---

### 2.2. Minimal visual noise

Не использовать большое количество:

- декоративных элементов;
- градиентов;
- теней;
- badges;
- разных цветов;
- конкурирующих CTA.

Интерфейс должен выглядеть технологично и чисто.

---

### 2.3. Clear hierarchy

Каждый экран должен иметь очевидную визуальную иерархию:

**Page → Section → Product → Action**

Пользователь должен понимать структуру страницы без необходимости читать весь текст.

---

### 2.4. Consistency

Один и тот же элемент должен выглядеть одинаково на всех страницах.

Например:

- Button → один набор правил;
- Product Card → один компонент;
- Input → один компонент;
- Badge → один компонент.

Не создавать визуально похожие элементы вручную.

---

# 3. Color System

## Primary

| Token | HEX | Usage |
|---|---|---|
| `color-primary` | `#2563EB` | Primary CTA, links, accents |
| `color-primary-hover` | `#1D4ED8` | Hover state |
| `color-primary-light` | `#EFF6FF` | Light backgrounds |

## Text

| Token | HEX | Usage |
|---|---|---|
| `color-text` | `#111827` | Primary text |
| `color-text-secondary` | `#6B7280` | Secondary text |
| `color-text-muted` | `#9CA3AF` | Placeholder / muted text |

## Background

| Token | HEX | Usage |
|---|---|---|
| `color-background` | `#FFFFFF` | Main background |
| `color-background-secondary` | `#F8FAFC` | Secondary sections |
| `color-dark` | `#111827` | Hero / dark sections |

## Border

| Token | HEX | Usage |
|---|---|---|
| `color-border` | `#E5E7EB` | Borders, dividers |

## Semantic colors

| Token | HEX | Usage |
|---|---|---|
| `color-success` | `#16A34A` | In stock / success |
| `color-warning` | `#F59E0B` | Warning |
| `color-error` | `#DC2626` | Error / unavailable |

### Color rules

- Blue is the primary accent.
- Do not use primary blue for large decorative areas unless explicitly specified.
- Red is reserved for errors, unavailable products and urgent price/sale states.
- Green is reserved for positive status.
- Text should primarily use `#111827` and `#6B7280`.

---

# 4. Typography

## Font

**Inter**

Available weights:

- 400 Regular
- 500 Medium
- 600 SemiBold
- 700 Bold

---

## Desktop typography

| Token | Size | Weight | Usage |
|---|---:|---:|---|
| `display` | 48px | 700 | Hero |
| `h1` | 36px | 700 | Page title |
| `h2` | 28px | 700 | Section title |
| `h3` | 22px | 600 | Subsection |
| `body-lg` | 18px | 400/500 | Important text |
| `body` | 16px | 400 | Main text |
| `body-sm` | 14px | 400 | Secondary text |
| `caption` | 12px | 400/500 | Metadata |

---

## Mobile typography

| Token | Size | Weight |
|---|---:|---:|
| `display` | 32px | 700 |
| `h1` | 28px | 700 |
| `h2` | 24px | 700 |
| `h3` | 20px | 600 |
| `body` | 16px | 400 |
| `body-sm` | 14px | 400 |
| `caption` | 12px | 400/500 |

---

# 5. Layout Grid

## Desktop

Base design width:

**1440px**

Content max-width:

**1200px**

Grid:

**12 columns**

Column gap:

**24px**

Example:

```text
Viewport: 1440px

| 120px |<--------- 1200px --------->| 120px |
```

Content should remain centered.

---

## Tablet

Maximum content width:

**960px**

Grid:

**8 columns**

---

## Mobile

Base design width:

**375px**

Horizontal padding:

**16px**

Grid:

**4 columns**

Column gap:

**12px**

---

# 6. Spacing System

Use an 8-point spacing system.

Available values:

```text
4
8
12
16
24
32
40
48
64
80
96
```

Recommended usage:

| Context | Spacing |
|---|---:|
| Icon / text | 8px |
| Small internal spacing | 8–12px |
| Component padding | 16px |
| Related elements | 16–24px |
| Between blocks | 32–48px |
| Between sections | 64–80px |

Avoid arbitrary values such as 17px, 23px or 37px.

---

# 7. Border Radius

| Token | Value |
|---|---:|
| `radius-sm` | 6px |
| `radius-md` | 10px |
| `radius-lg` | 16px |
| `radius-xl` | 20px |
| `radius-pill` | 999px |

Usage:

- Inputs → 10px
- Buttons → 10px
- Product cards → 16px
- Category cards → 16px
- Badges → 6px
- Tags → 999px

---

# 8. Shadows

Use shadows sparingly.

## Card

```text
0 2px 8px rgba(15, 23, 42, 0.06)
```

## Card hover

```text
0 8px 24px rgba(15, 23, 42, 0.10)
```

The interface should not look heavily elevated.

---

# 9. Icons

Icon system:

**Lucide Icons**

Sizes:

- 16px — utility
- 20px — standard UI
- 24px — primary actions
- 32px — large visual elements

Do not mix icon families with different visual styles.

---

# 10. Buttons

## Primary

- Background: `color-primary`
- Text: white
- Height: 48px
- Horizontal padding: 16–20px
- Radius: 10px

States:

```text
Default
Hover
Active
Disabled
Loading
```

---

## Secondary

- Background: white
- Border: `color-border`
- Text: `color-text`
- Height: 48px
- Radius: 10px

---

## Ghost

- Transparent background
- No border
- Text: `color-primary`

---

## Mobile CTA

Primary CTA may use full available width.

Minimum touch target:

**44px**

Preferred button height:

**48px**

---

# 11. Header

## Desktop

Main header height:

**72px**

Structure:

```text
Logo
+
Catalog
+
Search
+
Phone
+
Compare
+
Favorites
+
Account
+
Cart
```

Secondary category navigation is placed below the main header.

---

## Mobile

Mobile header is a separate component.

Structure:

```text
[Menu] [Logo] [Cart]

[        Search        ]
```

Do not simply scale down the desktop header.

Mobile navigation should be optimized for touch interaction.

---

# 12. Search

## Desktop

Height:

**48px**

Structure:

```text
[ Search icon ][ Search products, SKU... ][ Clear ]
```

States:

```text
Default
Focus
Filled
Loading
Results
No results
```

---

## Mobile

Search occupies the available width with **16px horizontal page padding**.

Search is a primary navigation mechanism and must remain easily accessible.

---

# 13. Product Card

Product Card is a core reusable component.

Structure:

```text
┌─────────────────────┐
│ Favorite     Badge  │
│                     │
│       IMAGE         │
│                     │
├─────────────────────┤
│ Brand               │
│ Product name        │
│                     │
│ ● In stock          │
│                     │
│ 12 990 ₽            │
│ 14 990 ₽            │
│                     │
│ [ Add to cart ]     │
└─────────────────────┘
```

Desktop target width:

**~282px**

Four cards fit within the main 1200px content area with the defined grid.

---

## Product Card states

Create Figma variants:

```text
Default
Hover
Sale
New
Out of stock
Added to cart
Favorite
```

Do not create separate independent components for each state.

---

# 14. Category Card

Category Card contains:

- image;
- category name;
- optional product count.

Desktop:

**4 cards per row**

Mobile:

**2 columns** or horizontal scroll depending on the section.

Hover:

- subtle image scale;
- subtle shadow increase;
- clear text remains visible.

---

# 15. Badges

Supported badges:

```text
SALE
NEW
ХИТ
В наличии
Нет в наличии
```

Maximum recommended number:

**1–2 badges per card.**

Badges must not visually dominate the product.

---

# 16. Filters

Filter components:

- Checkbox
- Radio
- Price range
- Select
- Search inside filter
- Clear filters

States:

```text
Default
Selected
Hover
Disabled
Expanded
Collapsed
```

---

## Mobile filters

Filters should open as a dedicated panel / bottom sheet.

Primary actions:

```text
Apply
Clear
```

The product list must remain easy to return to after applying filters.

---

# 17. Breadcrumbs

Structure:

```text
Главная / Каталог / Ноутбуки / Product
```

Rules:

- secondary visual priority;
- 14px;
- muted text;
- current page may use primary text color;
- on mobile, simplify or truncate when necessary.

---

# 18. Tabs

Used for:

- product information;
- product specifications;
- reviews;
- related information.

States:

```text
Default
Hover
Active
Disabled
```

Active tab uses primary blue.

---

# 19. Forms

Input:

- Height: 48px
- Radius: 10px
- Padding: 16px
- Border: `color-border`

States:

```text
Default
Focus
Filled
Error
Disabled
```

Error state:

- border: `color-error`
- supporting error message below input.

---

# 20. Product Page

Product page structure:

```text
Breadcrumbs

Product title
SKU
Rating / reviews

┌───────────────┬──────────────────────┐
│               │ Product name         │
│ Product       │ Price                │
│ images        │ Availability         │
│               │ Quantity             │
│               │ Add to cart          │
│               │ Buy now              │
└───────────────┴──────────────────────┘

Specifications
Description
Delivery
Warranty
Reviews
Related products
Recently viewed
```

Primary purchase information must remain above the fold where possible.

---

# 21. Catalog Page

Structure:

```text
Header

Breadcrumbs
H1
Category navigation

┌────────────┬──────────────────────────┐
│ Filters    │ Sort / count             │
│            │                          │
│            │ Product grid             │
│            │ Product grid             │
└────────────┴──────────────────────────┘

Pagination
```

Desktop:

- filters on the left;
- products on the right.

Mobile:

- filters become a separate control/panel;
- product grid uses 2 columns.

---

# 22. Homepage

Homepage structure:

```text
Header
Category navigation

Hero

Benefits

Popular categories

Popular products

Consultation / B2B section

Additional benefits

Footer
```

The homepage is both:

1. a product discovery surface;
2. a navigation point into the catalog.

---

# 23. Cart

Cart structure:

```text
Cart title

Product
Image
Name
Price
Quantity
Remove

Order summary

Subtotal
Delivery
Total

[ Checkout ]
```

Required states:

```text
Empty cart
Cart with products
Product quantity changed
Product removed
```

---

# 24. Checkout

Checkout should be divided into clear steps:

```text
1. Contact information
2. Delivery method
3. Address / pickup point
4. Payment
5. Order review
6. Confirmation
```

Delivery options:

- Pickup
- Courier
- Transport company

---

# 25. Mobile Rules

Mobile is not a scaled-down desktop version.

Mobile layouts must prioritize:

- touch;
- readability;
- one-handed interaction;
- large CTA;
- short information blocks;
- accessible filters;
- fast product scanning.

Recommended:

- page padding: 16px;
- CTA height: 48px;
- product grid: 2 columns;
- product image remains visually dominant;
- avoid overly dense tables;
- horizontal scrolling may be used for category/product carousels.

---

# 26. Responsive Behavior

### Desktop → Mobile

| Component | Desktop | Mobile |
|---|---|---|
| Header | Full navigation | Compact header |
| Search | Header search | Dedicated full-width search |
| Category navigation | Horizontal | Scroll / menu |
| Product grid | 4 columns | 2 columns |
| Filters | Sidebar | Panel / bottom sheet |
| Hero | Wide layout | Stacked layout |
| CTA | Auto width | Full width when appropriate |
| Tables | Full | Simplified / scrollable |
| Navigation | Multi-level | Drawer/menu |

---

# 27. Accessibility

Minimum requirements:

- sufficient text/background contrast;
- visible focus states;
- touch targets ≥ 44px;
- buttons must have clear labels;
- icons used as actions require accessible labels;
- form errors must be visible and understandable;
- do not communicate important information by color alone.

---

# 28. Figma Structure

Recommended Figma file structure:

```text
MODERN TECH
│
├── 00 — Cover
│
├── 01 — Design System
│   ├── Colors
│   ├── Typography
│   ├── Grid
│   ├── Spacing
│   ├── Radius
│   ├── Shadows
│   └── Icons
│
├── 02 — Components
│   ├── Header
│   ├── Navigation
│   ├── Search
│   ├── Buttons
│   ├── Inputs
│   ├── Product Card
│   ├── Category Card
│   ├── Badges
│   ├── Filters
│   ├── Breadcrumbs
│   ├── Tabs
│   ├── Pagination
│   ├── Cart
│   └── Footer
│
├── 03 — Desktop
│   ├── Homepage
│   ├── Catalog
│   ├── Category
│   ├── Product
│   ├── Search
│   ├── Cart
│   └── Checkout
│
├── 04 — Mobile
│   ├── Homepage
│   ├── Catalog
│   ├── Category
│   ├── Product
│   ├── Search
│   ├── Cart
│   └── Checkout
│
└── 05 — Dev
```

---

# 29. Component Rules

All reusable UI elements should be implemented as Figma components.

Use variants for states.

Example:

```text
Button
├── Type: Primary / Secondary / Ghost
├── State: Default / Hover / Active / Disabled
└── Size: Desktop / Mobile
```

Product Card:

```text
Product Card
├── State
├── Badge
├── Favorite
└── Cart state
```

Components should use:

- Auto Layout;
- reusable styles;
- variables/tokens where appropriate;
- consistent naming;
- responsive constraints.

Avoid detached copies of components unless required for a specific exception.

---

# 30. Naming Convention

Use English names for Figma components and development tokens.

Examples:

```text
Button/Primary
Button/Secondary
Input/Default
Input/Error
Card/Product
Card/Category
Navigation/Header
Navigation/Mobile
Badge/Sale
Badge/New
Filter/Checkbox
```

Design tokens:

```text
color-primary
color-text
color-border
radius-md
spacing-16
spacing-24
font-body
```

---

# 31. Development Handoff

Figma is the **source of truth for visual design**.

GitHub is the **source of truth for implementation tasks and code**.

Each development task should reference the relevant Figma frame/component.

Example:

```text
GitHub Issue #24

Title:
Implement Product Card

Figma:
[link to Product Card component]

Requirements:
- Match Figma dimensions
- Use approved typography
- Implement all states
- Implement responsive mobile version
- Add hover state
- Add cart state

Acceptance criteria:
- Desktop matches Figma
- Mobile matches Figma
- All states work
- No visual regressions
```

---

# 32. Source of Truth

Priority of sources:

1. Approved Figma Design System
2. Approved Figma components
3. Approved Figma page designs
4. This DESIGN.md
5. GitHub implementation

If a visual implementation conflicts with the approved Figma design, the discrepancy should be reviewed before implementation is considered complete.

---

# 33. Current Project Status

### Approved

- Modern Tech visual concept
- Desktop visual direction
- Design System v1.0
- Responsive approach
- Main site structure

### Next steps

1. Build Design System in Figma
2. Build reusable Components
3. Build Desktop pages
4. Build Mobile pages
5. Review and approve Figma
6. Prepare developer handoff
7. Connect development workflow
8. Create GitHub implementation tasks
9. Start development

---

**Modern Tech Design System v1.0 — Approved**