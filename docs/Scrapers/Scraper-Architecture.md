# Scrapers — Fleet Architecture

This document describes the design, execution flow, anti-bot mechanisms, and storage targets for the active scraper fleet in [`Backend/Data_Collection/Scrapers/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers).

---

## 🚀 Active Scrapers Overview

```
Scrapers Fleet
├── Retailer Scrapers (Prices, Stock & Commercial SKUs)
│   ├── PrimeABGB: Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py (V2 Delta-Only)
│   └── EliteHubs: Backend/Data_Collection/Scrapers/Elite Hubs/Bulk_data.py (Processors)
└── Reference Scrapers (Ground-Truth Silicon Specs & Variants)
    ├── TechPowerUp CPUs: Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/scraper.py (100% complete)
    └── TechPowerUp GPUs: Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py (In progress)
```

---

## 1. PrimeABGB Pipeline (V2 Concurrent Delta-Only)

* **Entry Point:** [`Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py)
* **Legacy Note:** The old two-stage split (`Bulk_data.py` generating JSONs + `Async_Scraper.py` reading JSONs) has been **fully deprecated and removed**. `Async_Scraper.py` has been deleted from the working tree.
* **Categories Scraped:** `cpu`, `gpu`, `motherboard`, `ram`, `ssd/hdd`, `cabinets`, `psu`, `cooler`.

### 3-Stage Execution Flow
1. **Stage 1: Listing Scan & Price/Stock Sync**
   - Automatically paginates WooCommerce catalog grids (`/page/N/`).
   - Extracts product URL, current price, original price, discount percentage, availability, and thumbnail URL.
   - Immediately executes `bulk_update_prices_from_listing()` in MongoDB using `UpdateOne` with `$set` and `$setOnInsert` to ensure existing products have live pricing without waiting for full detail crawls.
2. **Stage 2: Detail Delta Crawl**
   - Inspects existing MongoDB records and identifies "deltas" (newly discovered URLs or products lacking full specification payloads).
   - Launches concurrent asynchronous Playwright worker pages sharing a single optimized `BrowserContext`.
   - Extracts complete tabular specifications from description tabs and specifications tables.
   - For GPUs, executes `GPUCanonicalMatcher.get_instance(db).match(...)` to attach `canonical_gpu_id`, brand, and physical dimensions before persisting.
3. **Stage 3: Image Recovery Pipeline**
   - Independent asynchronous pipeline using `aiohttp`.
   - Downloads product imagery directly to [`Frontend/public/product_images/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/public/product_images) so the Next.js frontend can serve static images with zero middleware overhead.

---

## 2. EliteHubs Pipeline

* **Entry Point:** [`Backend/Data_Collection/Scrapers/Elite Hubs/Bulk_data.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/Elite Hubs/Bulk_data.py)
* **Target Category:** Desktop processors from `https://www.elitehubs.com/collections/processor`.
* **Mechanism:**
  - Scrapes Shopify product collection pages.
  - Downloads page snapshots and extracts OpenGraph metadata (title, price, stock, image URL) and available specifications.
  - Applies random jitter delays (0.6s–1.2s) between item requests to maintain respectful scraping boundaries.

---

## 3. TechPowerUp Reference Specification Scrapers

Reference scrapers gather hardware facts (architecture, socket, memory bus, clock speeds, TDP, die size) independent of retailer listing inaccuracies.

### A. TechPowerUp CPU Scraper
* **File:** [`Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/scraper.py)
* **Scope:** Desktop CPUs from 2018 onward.
* **Target Collection:** `PC_Parts.raw_cpu_reference`.
* **Status:** **539 / 539 CPUs scraped (100% complete)**.
* **Integrity:** Verified **0 duplicate slugs, 0 duplicate display names** via `check_duplicates.py`.

### B. TechPowerUp GPU Scraper
* **File:** [`Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py)
* **Scope:** Desktop GPUs from 2017 onward.
* **Target Collection:** `PC_Parts.raw_gpu_reference`.
* **Discovery:** 245 total GPUs identified in `data/discovery_2026-06-02.json`.
* **Status:** **95 / 245 scraped (~38.8% complete)**. 150 GPUs remain to be scraped ([GitHub Issue #3](https://github.com/Agam-Ramteke/loop-pc-builder/issues/3)).
* **Resume Support:** Automatically queries existing `tpu_url` values in MongoDB on startup and filters out already-scraped records.
* **Features:**
  - Generates deterministic candidate identities (`generate_candidate_identity`).
  - Scrapes raw board variant tables with unique `variant_key` hashing.
  - Runs in-memory schema coverage audits (`AUDIT_ALIASES`) to guard against spec layout drift.

---

## 🛡️ Anti-Bot & Stealth Configuration

TechPowerUp and retailer sites employ Cloudflare and custom proof-of-work (PoW) bot protection. The scraper fleet handles this via:

1. **Resource Blocking:**
   - Blocks heavy assets to conserve bandwidth and minimize canvas fingerprinting:
     `{"image", "media", "font", "other"}`
   - Blocks third-party telemetry scripts (Google Analytics, Hotjar, Facebook, AdRoll).
2. **Human-Like Delay & Jitter:**
   - Listing page navigation delay: `5.0 – 10.0` seconds.
   - Detail page navigation delay: `10.0 – 20.0` seconds per worker.
   - Pre-request jitter: `2.5 – 6.0` seconds.
3. **Challenge Detection & Backoff:**
   - Monitored challenge strings: `"Checking your browser"`, `"Just a moment"`, `"bot check in progress"`, `".firewall"`, `"pow-progress-bar"`.
   - On challenge detection, backoff exponentially (`CF_BACKOFF_BASE = (15, 30)`s) or pause gracefully rather than attempting aggressive evasion.
4. **Crash Recovery & Snapshots:**
   - Saves intermediate HTML snapshots to `snapshots/` during parser exceptions to allow offline debugging without re-triggering requests.

---

## 🔗 Related Documentation & Issues
- [[Decisions/ADR-003-PrimeABGB-V2-Delta-Scraper|ADR-003: PrimeABGB V2 Delta Scraper]]
- [[Data-Pipeline/Data-Flow|Data Flow & Ingestion Lifecycle]]
- [[GPU-Normalization/Canonicalization|GPU Normalization & Canonical Matching]]
- **Tracking Issues:**
  - [Issue #3](https://github.com/Agam-Ramteke/loop-pc-builder/issues/3): Complete TechPowerUp GPU reference scraping (P0)
  - [Issue #4](https://github.com/Agam-Ramteke/loop-pc-builder/issues/4): Add GPU reference scrape coverage and quality audit (P0)
  - [Issue #5](https://github.com/Agam-Ramteke/loop-pc-builder/issues/5): Audit PrimeABGB V2 delta scraper metrics and failure recovery (P1)
  - [Issue #8](https://github.com/Agam-Ramteke/loop-pc-builder/issues/8): Complete missing retailer component categories (P1)
  - [Issue #9](https://github.com/Agam-Ramteke/loop-pc-builder/issues/9): Harden scraper regression tests and idempotent upserts (P2)
