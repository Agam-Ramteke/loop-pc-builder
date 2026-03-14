# Scraping Notes
Up-to-date reference for the active scrapers in this repo.

---

---

## PrimeABGB pipeline (`Backend/Data_Collection/Scrapers/PrimeABGB`)

### Stage 1: Category listings (`Bulk_data.py`)
- Asynchronously scrapes WooCommerce category grids for: `processor`, `graphics-card`, `ram`, `ssd`, `hdd`, `motherboard`, `smps`, `cabinet`, `cpu-cooler`.
- Handles pagination automatically (WooCommerce `/page/N/` structure).
- Filters out "external" or "portable" drives during the listing phase for HDD/SSD.
- Saves daily JSONs to `data/<category>_YYYY-MM-DD.json`.
- Automatically checks for and reports duplicate products across JSON files after scraping.

### Stage 2: Product ingest (`Async_Scraper.py`)
- Reads URLs from `Bulk_data` JSONs, downloads detail pages, and upserts to MongoDB.
- Collection mapping: `ssd` & `hdd` → `Storage`, others map to standard capitalized names (`Processors`, `GPUs`, etc.).
- Freshness guard: 2-day limit for re-scraping.
- Fallback logic: If detail-page parsing fails to find prices, it preserves the listing-level prices from Stage 1.
- CLI:
  - `python Async_Scraper.py` (processes all stale categories).
  - `--category <slug>` to target a specific category.
  - `--force` to ignore freshness and re-scrape all.

### Shared helpers (`common_functions.py`)
- WooCommerce-specific HTML parsers for listing and product detail pages.
- Priority-based specification extraction (prefers description table over additional info tab).
- Secure upsert logic using `$set` and `$setOnInsert` to prevent data loss.

---

## EliteHubs scraper (`Backend/Data_Collection/Scrapers/Elite Hubs/elitehubs.py`)
- Focused on the processors collection at `https://www.elitehubs.com/collections/processor`.
- Flow:
  1) Download collection page snapshot, extract unique product URLs.  
  2) Download each product page to a temp file, parse OG meta for title/image/price + basic stock heuristics.  
  3) Save to `data/processors_<YYYY-MM-DD>.json`.
- Polite scraping with random 0.6–1.2s delay per product.
- Cleans up temp HTML files immediately; prunes JSONs older than 7 days.

---

## Operational notes
- MongoDB connection defaults to `mongodb://localhost:27017/` (DB: `PC_Parts`).
- Scrapers use `curl_cffi` for Chrome TLS impersonation to bypass bot detection (Cloudflare/WAF).
- Data outputs are stored in respective `data/` directories; snapshots are temporary.
- Image storage:
  - PrimeABGB: `Backend/Data_Collection/Scrapers/PrimeABGB/product_images/`
- As of 2026-03-14, the pipeline is fully asynchronous and supports partial/forced updates.