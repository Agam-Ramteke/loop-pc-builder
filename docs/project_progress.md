# Project Progress & Status Report

**Project:** Loop – PC Part Picker
**Date:** September 27, 2026
**Active Branch:** `Asynchronous-DB-Updation`
**Latest Commit:** `edb13a3` (*"Before moving to Pstgresql"*)

> [!NOTE] Snapshot Observation Notice
> The metrics and document counts reported in this document represent local database checkpoints observed on September 27, 2026 and November 13, 2026. For active task tracking and sprint status, consult [[Roadmap/Engineering-Roadmap|Engineering Roadmap]] and GitHub Issues #3–#20.

---

## 1. Executive Summary

Loop is undergoing a major architectural evolution, migrating from a flat, document-based MongoDB storage model to a **two-layer relational architecture** (PostgreSQL/Supabase) while maintaining a resilient, asynchronous ingestion pipeline and a modern Next.js 16 frontend.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             DATA INGESTION                                  │
│  PrimeABGB (WooCommerce) ──┐                                                │
│  Elite Hubs (Shopify)     ──┼──> [Backend/Data_Collection]                  │
│  TechPowerUp (Ref Specs)  ──┘         │                                     │
│                                       ▼                                     │
│                             CANONICAL PIPELINE                              │
│                      [gpu_matcher.py] (4-stage regex/VRAM)                  │
│                                       │                                     │
│         ┌─────────────────────────────┴─────────────────────────────┐       │
│         ▼                                                           ▼       │
│  [MongoDB: PC_Parts]                                    [PostgreSQL: Relational]    │
│  • Raw & current retail store collections                • 2-layer schema (Chips vs Products)
│  • Primary active data store for Next.js API            • Staged via export/load seeds
│                                                                             │
│                                       │                                     │
│                                       ▼                                     │
│                              NEXT.JS 16 FRONTEND                            │
│           • Unified Component API (`/api/components`) + Redis Caching       │
│           • Custom Builder (`/builder`) & Catalog Browse (`/browse`)        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion & Reference Scraping Layer

### A. TechPowerUp Reference Scrapers

To power the canonical specification layer without relying on messy retailer descriptions, standalone scrapers for TechPowerUp databases were developed under [`Backend/Data_Collection/Scrapers/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers):

* **CPU Reference Scraper ([`TechPowerUp_CPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/scraper.py)):**
  * **Scope:** Desktop CPUs from 2018 onward.
  * **Discovery:** 539 total CPUs discovered ([`discovery_2026-06-01.json`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/data/discovery_2026-06-01.json)).
  * **Database Status:** **539 / 539 scraped into MongoDB `raw_cpu_reference` (100% complete)**.
  * **Data Integrity:** **0 duplicate slugs, 0 duplicate display names** verified via [`check_duplicates.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/check_duplicates.py).

* **GPU Reference Scraper ([`TechPowerUp_GPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py)):**
  * **Scope:** Desktop GPUs from 2017 onward.
  * **Discovery:** 245 total GPUs discovered ([`discovery_2026-06-02.json`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/data/discovery_2026-06-02.json)).
  * **Database Status:** **95 / 245 scraped into MongoDB `raw_gpu_reference` (~38.8% complete)**.
  * **Features:** Extracts raw specifications, board variant tables, and generates deterministic variant keys.

---

## 3. Canonical Pipelines & Normalization

### A. GPU Canonical Matcher ([`Backend/Data_Collection/Pipelines/gpu_matcher.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Pipelines/gpu_matcher.py))

* **Algorithm:** Deterministic 4-stage matching:
  1. Chip Series extraction from retailer specs.
  2. Regex extraction of GPU family/generation from title.
  3. Memory size / VRAM disambiguation (e.g. distinguishing RTX 5060 Ti 8GB vs 16GB, RTX 3050 6GB vs 8GB).
  4. Normalized key lookup against canonical database records.
* **Unit Testing:** **46/46 tests passing** ([`test_gpu_matcher.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Pipelines/test_gpu_matcher.py)).
* **Reference Library:** 1,908 reference GPUs in [`consumer_gpus.json`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/All_GPUs/consumer_gpus.json); 645 desktop consumer GPUs loaded into MongoDB `canonical_gpus`.
* **Match Evaluation:** Evaluated across all **726 live MongoDB GPUs**:
  * **715 / 726 matched successfully (98.5% match rate)**.
  * The 11 unmatched are enterprise/workstation GPUs (Radeon AI PRO R9700, Radeon Pro W7800, NVIDIA RTX PRO 4500 Blackwell Server Edition) intentionally excluded by consumer desktop filters.

### B. Retailer Ingestion Integration

* **PrimeABGB ([`Bulk_data.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py)):**
  * Converted to V2 Concurrent, Delta-Only architecture.
  * Integrated directly with `gpu_matcher` during upsert to automatically attach `canonical_gpu_id`, `brand`, and physical dimensions on ingestion.
* **Active MongoDB (`PC_Parts`) Counts:**
  * `GPUs`: 726 documents
  * `Processors`: 162 documents
  * `Motherboards`: 638 documents
  * `RAM`: 227 documents
  * `canonical_gpus`: 645 documents
  * `raw_cpu_reference`: 539 documents
  * `raw_gpu_reference`: 95 documents

---

## 4. PostgreSQL Relational Migration

A dual-layer relational schema is defined in [`Backend/db/schema.sql`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/db/schema.sql) and documented in [`docs/postgres_migration.md`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/docs/postgres_migration.md):

1. **Canonical Chip Tables (`gpu_chips`, `cpu_chips`):** Silicon-level facts (architecture, socket, cores, TDP, clock speeds, VRAM, memory channels).
2. **Retailer Product Tables (`gpu_products`, `cpu_products`):** Store-specific SKUs, pricing (INR), availability, URLs, and image links.

### Local Staging Database (`loop_pc_builder` in PostgreSQL):

| Table | Current Rows | Role | Status |
| :--- | :---: | :--- | :--- |
| `gpu_chips` | **64** | Canonical silicon specifications | Populated via seed exporter |
| `gpu_products` | **773** | Retail listings / SKUs | Populated via seed exporter |
| `cpu_chips` | **138** | Canonical CPU specifications | Populated via seed exporter |
| `cpu_products` | **157** | Retail listings / SKUs | Populated via seed exporter |

* Seed generation script: [`Backend/scripts/export_postgres_seed.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/scripts/export_postgres_seed.py)
* Seed loader script: [`Backend/scripts/load_postgres_seed.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/scripts/load_postgres_seed.py)
* Generated seed data: [`Backend/generated_data/postgres/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/generated_data/postgres/)

---

## 5. Frontend & Web Application

* **Tech Stack:** Next.js 16.1.6 (App Router), React 19.2.3, Tailwind CSS v4, Framer Motion, Lucide React, ioredis, MongoDB driver.
* **Unified API:** [`Frontend/src/app/api/components/route.ts`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/api/components/route.ts) with dynamic aggregation pipelines, price parsing, and Redis caching (120s TTL).
* **Pages & Features:**
  * **Landing Page:** Interactive starfield canvas, category cards, featured components ([`page.tsx`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/page.tsx)).
  * **Catalog Browse:** Multi-filter, category tabs, sort dropdowns, URL state synchronization ([`browse/page.tsx`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/browse/page.tsx)).
  * **PC Builder:** Custom builder interface and recommendation engine ([`builder/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/builder)).
* **Code Health & Lint Status:**
  * ESLint identified 6 errors:
    * React 19 / Next 16 hook lint warnings for synchronous `setState` in `useEffect` ([`Navbar.tsx`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/components/Navbar.tsx#L18), [`ThemeToggle.tsx`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/components/ThemeToggle.tsx#L12)).
    * Explicit `any` types in [`page.tsx`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/page.tsx#L462).

---

## 6. Action Items & Roadmap

> [!NOTE] Authoritative Task Tracker
> For current task assignment and issue states, refer to [[Roadmap/Engineering-Roadmap|Engineering Roadmap]] and GitHub Issues (#3–#20).

| Task | Priority | Component | Details | Status / Issue |
| :--- | :---: | :--- | :--- | :---: |
| **Finish TPU GPU Scraper** | High | Scrapers | Resume [`TechPowerUp_GPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py) to complete the remaining 150 GPUs (95/245 done). | **In Progress** ([Issue #3](https://github.com/Agam-Ramteke/loop-pc-builder/issues/3)) |
| **Backfill MongoDB GPUs** | High | Pipelines | Attached canonical IDs to all 715 matched GPUs via `gpu_matcher`. | **Completed** (715/726 verified) |
| **Fix Frontend ESLint Errors** | Medium | Frontend | Refactor `useEffect` in `Navbar.tsx` and `ThemeToggle.tsx` and replace `any` types in `page.tsx`. | **Open** ([Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17)) |
| **Scrape Remaining Categories** | Medium | Scrapers | Trigger PrimeABGB runs for Storage, SMPS, Cabinets, and CpuCoolers to restock missing catalog sections. | **Open** ([Issue #8](https://github.com/Agam-Ramteke/loop-pc-builder/issues/8)) |
| **Cut Over API to PostgreSQL** | Roadmap | Backend / API | Transition Next.js API `/api/components` to query PostgreSQL (`gpu_chips` + `gpu_products`, `cpu_chips` + `cpu_products`). | **Staged** ([Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14)) |
