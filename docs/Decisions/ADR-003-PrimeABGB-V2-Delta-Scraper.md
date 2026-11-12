# ADR-003: PrimeABGB Scraper V2 (Concurrent Delta-Only) Architecture

* **Status:** Accepted (Implemented & Verified)
* **Date:** September 2026
* **Deciders:** Agam Ramteke
* **Implementation File:** `Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py`
* **Deprecated File:** `Backend/Data_Collection/Scrapers/PrimeABGB/Async_Scraper.py` (Deleted)
* **Related Issues:** [Issue #5](https://github.com/Agam-Ramteke/loop-pc-builder/issues/5), [Issue #7](https://github.com/Agam-Ramteke/loop-pc-builder/issues/7)

---

## Context & Problem Statement

The original PrimeABGB scraping pipeline relied on a disconnected two-step model:
1. `Bulk_data.py` downloaded listing pages and dumped daily JSON files into `data/<category>_YYYY-MM-DD.json`.
2. `Async_Scraper.py` read URLs from these JSON files, visited product detail pages, and upserted records to MongoDB.

This workflow had several operational vulnerabilities:
- **High Redundancy & IP Burn:** Visiting hundreds of detail pages every run repeatedly triggered Cloudflare bot-detection challenges.
- **Out-of-Sync Prices:** Product prices change frequently, but specifications rarely change after launch. Re-scraping the entire product page just to update a price was wasteful.
- **Decoupled Failure Handling:** If step 1 succeeded but step 2 failed, intermediate files lingered, and prices were not updated in the database.

## Decision

Consolidate the entire PrimeABGB pipeline into a unified, V2 Concurrent Delta-Only scraper in [`Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py), and delete `Async_Scraper.py`:

1. **Stage 1 (Listing & Price Sync):**
   - Catalog pagination extracts price, original price, discount, and stock.
   - Updates MongoDB immediately via bulk `UpdateOne` operations with `$set`.
2. **Stage 2 (Delta Detail Fetch):**
   - Detail pages are fetched only for items that are newly inserted or lack specifications.
   - Concurrent asynchronous Playwright pages share a single `BrowserContext` to conserve system memory.
3. **Stage 3 (Decoupled Image Ingestion):**
   - Product images are downloaded via `aiohttp` directly to `Frontend/public/product_images/`.
4. **Embedded Canonical Matching:**
   - For graphics cards, `gpu_matcher.py` is invoked inside the upsert pipeline to attach `canonical_gpu_id` upon ingestion.

## Consequences

* **Positive:**
  - Dramatically reduced total request count by skipping detail visits for unchanged products.
  - Price updates happen in minutes during Stage 1 rather than hours.
  - Eliminated disk-bound JSON file intermediates and sync bugs between steps.
  - Images are placed directly in the Next.js static asset folder.
* **Trade-offs:**
  - Requires documentation updates across existing notes that previously referred to `Async_Scraper.py`.
