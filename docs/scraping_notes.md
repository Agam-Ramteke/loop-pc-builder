# Scraping Notes

Reference guide for the active scraper fleet in [`Backend/Data_Collection/Scrapers/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers).

> [!NOTE] Architecture Migration Notice
> For comprehensive scraper fleet documentation, anti-bot mitigation strategies, and crawler benchmarks, refer to **[[Scrapers/Scraper-Architecture|Scraper Fleet Architecture]]**.

---

## 1. PrimeABGB Pipeline (`Backend/Data_Collection/Scrapers/PrimeABGB/Bulk_data.py`)

* **Architecture:** V2 Concurrent Delta-Only Scraper (consolidated into `Bulk_data.py`).
* **Deprecation Notice:** The legacy two-step workflow involving `Async_Scraper.py` has been **removed**. `Async_Scraper.py` has been deleted from the repository.

### Workflow Stages:
1. **Stage 1 (Category Listing & Live Price Sync):**
   - Automatically paginates WooCommerce catalog grids (`/page/N/`) for: `cpu`, `gpu`, `motherboard`, `ram`, `ssd/hdd`, `cabinets`, `psu`, `cooler`.
   - Filters out non-internal drives during listing parse for storage categories.
   - Executes immediate atomic MongoDB price and stock updates (`bulk_update_prices_from_listing`) using `UpdateOne` with `$set` and `$setOnInsert`.
2. **Stage 2 (Detail Delta Crawl):**
   - Evaluates MongoDB records to identify items missing technical specifications.
   - Spawns concurrent Playwright browser pages sharing a single `BrowserContext` to extract full tabular specifications.
   - Integrates directly with [`Backend/Data_Collection/Pipelines/gpu_matcher.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Pipelines/gpu_matcher.py) to attach canonical GPU identifiers, brands, and card dimensions on ingestion.
3. **Stage 3 (Decoupled Image Recovery):**
   - Downloads product imagery asynchronously using `aiohttp`.
   - **Image Storage Path:** Images are saved directly to [`Frontend/public/product_images/`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/public/product_images) for direct serving via Next.js static asset routes.

---

## 2. EliteHubs Scraper (`Backend/Data_Collection/Scrapers/Elite Hubs/Bulk_data.py`)

* **Active Entry Point:** `Bulk_data.py` (replaces legacy references to `elitehubs.py`).
* **Target:** Desktop processors catalog at `https://www.elitehubs.com/collections/processor`.
* **Execution:**
  - Scrapes Shopify collection listings to identify unique product URLs.
  - Downloads product page snapshots and extracts OpenGraph metadata (title, price, stock, image URL).
  - Applies random request jitter (0.6s–1.2s delay per product) to maintain polite access.

---

## 3. Reference Specification Scrapers

Hardware reference scrapers collect ground-truth specifications from TechPowerUp to power canonical matching:

* **TechPowerUp CPU Scraper ([`TechPowerUp_CPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_CPUs/scraper.py)):**
  - Target: Desktop CPUs from 2018 onward.
  - Database: `PC_Parts.raw_cpu_reference`.
  - Status: **539 / 539 CPUs scraped (100% complete)**; 0 duplicate slugs or names.
* **TechPowerUp GPU Scraper ([`TechPowerUp_GPUs/scraper.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Scrapers/TechPowerUp_GPUs/scraper.py)):**
  - Target: Desktop GPUs from 2017 onward.
  - Database: `PC_Parts.raw_gpu_reference`.
  - Status: **95 / 245 scraped (~38.8% complete)**; 150 GPUs pending ([GitHub Issue #3](https://github.com/Agam-Ramteke/loop-pc-builder/issues/3)).
  - Includes board variant table extraction with deterministic `variant_key` hashing.

---

## ⚙️ Operational Environment
- **MongoDB Connection:** Default `mongodb://localhost:27017/` (Database: `PC_Parts`).
- **Browser Stealth:** Playwright with headless Chromium, resource blocking (tracking, fonts, images), and exponential backoff on Cloudflare/PoW challenges (`CF_BACKOFF_BASE = (15, 30)`s).
- **Snapshot Recovery:** Debug HTML snapshots saved to `async_snapshots/` and `snapshots/` during parser exceptions for safe offline debugging.
