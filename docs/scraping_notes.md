# Scraping Notes
Up-to-date reference for the active scrapers in this repo.

---

## MD Computers pipeline (`Backend/Data_Collection/Scrapers/MD_computers`)

### Stage 1: Category listings (`Bulk_data.py`)
- Asynchronously scrapes category grids for: processor, graphics-card, ram, storage, smps, cabinet, cpu-cooler.
- Saves daily JSONs to `data/<category>_YYYY-MM-DD.json` (skips categories already scraped today by default).
- CLI:
  - `python Bulk_data.py --all` (default) or `--categories processor,ram`
  - `--page-limit N` for quick tests, `--no-skip` to re-scrape today’s data.
- Produces lightweight records: name, URL, image URL (fallback across src/data-src/lazy/cfsrc), price (orig/discounted), timestamp, source.
- Displays a Rich summary table of new or existing files.

### Stage 2: Product ingest (`Async_Scraper.py`)
- Reads one or more JSON files from `data/`, downloads product pages concurrently, parses details, and upserts into MongoDB.
- Collection mapping: processors → `Processors`, graphics-card → `GPUs`, ram → `RAM`, smps → `SMPS`, storage → `Storage`, cabinet → `Cabinets`, cpu-cooler → `CpuCoolers`, motherboard → `Motherboards` (fallback to capitalized slug).
- Freshness guard: skips products scraped within the last 2 days (based on `scraped_at` in Mongo).
- Parsing uses `common_functions.parse_product_page`: extracts name, old/new prices, discount, stock status, specifications table, and downloads product images (with hash-based dedupe and DB checks).
- After processing a file it:
  - Cleans up HTML snapshots in `async_snapshots/`
  - Runs `async_recover_missing_images` to redownload missing image files across collections
  - Runs `async_remove_non_internal_storage` to drop non-internal drives from the Storage collection
- CLI:
  - `python Async_Scraper.py --all` (process every JSON)
  - `python Async_Scraper.py --file <name>.json` to target one file
  - `--limit N` to cap items per file, `--dry` to parse without DB writes
- Stores images in `product_images/` and snapshots in `async_snapshots/`.

### Shared helpers (`common_functions.py`)
- Safe filenames/slugging, JSON save with automatic pruning (older than 2 days for same prefix).
- Async snapshot downloader with retry/backoff (`download_with_retry`), image URL extraction helpers.
- Mongo upsert helper with freshness check and flexible unique keys.
- Async image recovery for missing files and category-specific cleanup utilities.

---

## EliteHubs scraper (`Backend/Data_Collection/Scrapers/Elite Hubs/elitehubs.py`)
- Focused on the processors collection at `https://www.elitehubs.com/collections/processor`.
- Flow:
  1) Download collection page snapshot, extract unique product URLs.  
  2) Download each product page to a temp file, parse OG meta for title/image/price + basic stock heuristics.  
  3) Save to `data/processors_<YYYY-MM-DD>.json`.
- Polite scraping with random 0.6–1.2s delay per product.
- Cleans up temp HTML files immediately; prunes JSONs older than 7 days.
- Run via:
```bash
cd "Backend/Data_Collection/Scrapers/Elite Hubs"
python elitehubs.py
```

---

## Operational notes
- MongoDB connection for MD Computers ingest defaults to `mongodb://localhost:27017/` (DB: `PC_Parts`).
- Job runner (`Backend/api.py`) can invoke `Bulk_data.py` and `Async_Scraper.py` remotely; see `README.md` for API usage.
- Data outputs as of 2025-12-09 are stored in `Backend/Data_Collection/Scrapers/MD_computers/data/` (daily per category) and `Backend/Data_Collection/Scrapers/Elite Hubs/data/`.