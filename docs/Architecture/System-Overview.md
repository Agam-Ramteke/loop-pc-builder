# Architecture — System Overview

This document outlines the end-to-end architecture of **Loop PC Builder**, describing how raw retailer data and reference hardware specifications are scraped, normalized, persisted, and served to end users.

---

## 🏗️ High-Level System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               1. DATA INGESTION FLEET                                  │
│                                                                                        │
│   [Retailers: PrimeABGB, EliteHubs]             [Reference: TechPowerUp CPU & GPU]     │
│   • HTML / WooCommerce / Shopify                • Desktop specs from 2017/2018 onward  │
│   • Stealth browser workers (Playwright)        • Anti-bot / PoW backoff handling      │
│   • Delta detection (only scrape new/stale)     • Complete specs & variant tables      │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           2. NORMALIZATION & CANONICAL MATCHING                        │
│                                                                                        │
│   [Backend/Data_Collection/Pipelines/gpu_matcher.py]                                    │
│   • 4-stage deterministic matching: Specs -> Title Regex -> VRAM -> Canonical ID       │
│   • Disambiguates VRAM tiers (e.g. RTX 5060 Ti 8GB vs 16GB, RTX 3050 6GB vs 8GB)       │
│   • Brand & physical dimension extraction (length, slots, display outputs)             │
│   • Unit tested: 46/46 passing tests; 98.5% live match rate on 726 retail GPUs        │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 3. DATA STORAGE LAYER                                  │
│                                                                                        │
│   ┌────────────────────────────────────────┐  ┌─────────────────────────────────────┐  │
│   │  PRIMARY ACTIVE STORE: MongoDB 8.x     │  │  TARGET RELATIONAL STORE: PostgreSQL│  │
│   │  Database: PC_Parts                    │  │  Database: loop_pc_builder (schema) │  │
│   │  • GPUs (726 docs, 715 canonical IDs)  │  │  • gpu_chips (Canonical silicon)    │  │
│   │  • Processors (162 docs)               │  │  • gpu_products (Retailer SKUs)     │  │
│   │  • Motherboards (638 docs)             │  │  • cpu_chips (Canonical silicon)    │  │
│   │  • RAM (227 docs)                      │  │  • cpu_products (Retailer SKUs)     │  │
│   │  • raw_cpu_reference (539 docs)        │  │  • Staged via export_postgres_seed  │  │
│   │  • raw_gpu_reference (95 docs)         │  │  • Dual-layer relational isolation  │  │
│   └────────────────────────────────────────┘  └─────────────────────────────────────┘  │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              4. API & PRESENTATION LAYER                               │
│                                                                                        │
│   [Next.js 16 (App Router) & React 19 Frontend]                                        │
│   • Unified Component API (/api/components) using dynamic MongoDB aggregation pipelines│
│   • High-speed Redis Cache Layer (120s TTL) for product queries & search filters       │
│   • Interactive UI: Starfield canvas, glassmorphism, category filters, responsive grid │
│   • PC Builder & Compatibility Engine: Socket, memory, TDP, and dimension clearance   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Core Architectural Components

### 1. Ingestion Layer
- **PrimeABGB Pipeline (`Bulk_data.py`):** Operates on a concurrent delta-first model. Listing pages are scraped to immediately update live prices and stock in MongoDB. Detail pages are scraped asynchronously only for missing or newly discovered products. Integrates the GPU canonical matcher on ingestion.
- **EliteHubs Pipeline (`Bulk_data.py`):** Dedicated Shopify scraper for processors, capturing title, pricing, stock, and OpenGraph metadata.
- **TechPowerUp Reference Scrapers (`TechPowerUp_CPUs`, `TechPowerUp_GPUs`):** Ground-truth hardware databases used to establish canonical silicon specifications, variant lists, and pinouts independent of noisy retailer titles.

### 2. Normalization & Canonicalization Layer
- Solves the core industry challenge where each retailer describes the same underlying silicon using varying names, abbreviations, and marketing fluff.
- Employs a deterministic, rule-based approach rather than fuzzy matching to prevent dangerous misclassifications (e.g. confusing DDR4 with DDR5 motherboards, or 8GB with 16GB GPU variants).
- See [[GPU-Normalization/Canonicalization]] for detailed algorithm breakdown and unit test evidence.

### 3. Data Storage & Relational Evolution
- **Current State:** Serving directly from MongoDB `PC_Parts`. This preserves operational stability and lets scrapers write unstructured and semi-structured payloads without schema lockups.
- **Target Architecture:** Two-layer relational model in PostgreSQL/Supabase (`Backend/db/schema.sql`).
  - **Silicon Layer:** `gpu_chips`, `cpu_chips` contain architectural specifications, TDP, cache, memory channels, sockets, and hardware dimensions.
  - **Product Layer:** `gpu_products`, `cpu_products` contain store-specific listings, pricing (INR), inventory status, retailer product URLs, and image links.
  - See [[Decisions/ADR-001-Two-Layer-Relational-Schema]] for the migration strategy.

### 4. API & Frontend Serving Layer
- Built with **Next.js 16.1.6** (App Router) and **React 19.2.3**.
- Exposes `GET /api/components` backed by dynamic MongoDB aggregation pipelines and cached via **Redis** (120-second TTL).
- See [[API/API-Architecture]] and [[Frontend/Frontend-Architecture]].

---

## 🔗 Related Documentation
- [[Architecture/Technology-Stack|Technology Stack & Tooling]]
- [[Scrapers/Scraper-Architecture|Scraper Fleet Architecture]]
- [[Data-Pipeline/Data-Flow|Data Pipeline & Seeds Flow]]
- [[Decisions/ADR-001-Two-Layer-Relational-Schema|ADR-001: Two-Layer Relational Schema]]
