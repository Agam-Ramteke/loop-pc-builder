# Frontend — Architecture & UI Engineering

This document outlines the user interface, component architecture, styling framework, and rendering pipelines of the **Loop PC Builder** web application (`Frontend/`).

---

## 🎨 UI Architecture & Design System

The frontend is built on **Next.js 16.1.6 (App Router)** and **React 19.2.3**, styled with **Tailwind CSS v4** and animated via **Framer Motion**.

```
Frontend/
├── src/
│   ├── app/
│   │   ├── page.tsx               # Landing page (Starfield canvas, category grid)
│   │   ├── browse/page.tsx        # Component Catalog Browser (filters, search, sorts)
│   │   ├── builder/page.tsx       # Custom PC Builder & Compatibility interface
│   │   └── api/components/        # Backend-for-Frontend API endpoints
│   ├── components/
│   │   ├── Navbar.tsx             # Responsive global navigation
│   │   ├── ThemeToggle.tsx        # Dark/light mode switcher
│   │   └── Starfield.tsx          # Interactive physics canvas background
│   └── lib/
│       ├── componentData.ts       # Shared aggregation expressions & data mappers
│       ├── mongodb.ts             # Connection pooling for MongoDB driver
│       └── redis.ts               # Resilient Redis cache client
└── public/
    └── product_images/            # Decoupled static product images
```

---

## 🌟 Visual Features & UX Design

1. **Interactive Starfield Canvas:**
   - Real-time physics-based starfield particle background on the landing page responding to cursor movements and scroll speed.
2. **Glassmorphism Design Language:**
   - Semi-transparent backdrop blur surfaces (`backdrop-blur-md bg-white/10 dark:bg-black/30`) with subtle border glows.
3. **CSS Blend Mode Image Optimization:**
   - Retailer product thumbnails often feature solid white or off-white backgrounds that clash with dark theme palettes.
   - Instead of running expensive server-side computer vision background removal, images use CSS blend modes (`mix-blend-multiply` in light mode, invert/blend filters in dark mode) to blend seamlessly into container backgrounds.
4. **URL State Synchronization:**
   - The `/browse` page synchronizes all active category selections, search queries, price ranges, and pagination parameters to URL search params (`useSearchParams`), enabling shareable search states.

---

## ⚠️ Known Technical Debt & ESLint Status ([GitHub Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17))

During the Next.js 16 / React 19 upgrade, the following lint warnings were flagged:
- **Synchronous `setState` in `useEffect`:**
  - `Navbar.tsx#L18` and `ThemeToggle.tsx#L12` trigger React 19 hydration/effect warnings due to direct `setState` calls inside effects.
- **Unsafe `any` Types:**
  - `page.tsx#L462` contains explicit `any` declarations in component mapping pipelines.
- **Action Plan:**
  - Address in Week 4 ([Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17)) alongside merging input validation improvements from [PR #2](https://github.com/Agam-Ramteke/loop-pc-builder/pull/2).

---

## 🔗 Related Documentation & Issues
- [[Architecture/System-Overview|System Overview]]
- [[API/API-Architecture|API Architecture]]
- **Tracking Issues:**
  - [Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17): Resolve frontend lint/type warnings and review open API PR (P1)
  - [Issue #18](https://github.com/Agam-Ramteke/loop-pc-builder/issues/18): Build canonical component browser with retailer offer comparison (P1)
  - [Issue #19](https://github.com/Agam-Ramteke/loop-pc-builder/issues/19): Deliver PC builder MVP with compatibility feedback (P1)
