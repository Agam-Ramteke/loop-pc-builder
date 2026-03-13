"""
PrimeABGB — Async individual product-page scraper.

Reads product URLs from the Bulk_data JSON files, downloads a HTML snapshot
of each product page, parses it for full specs, and upserts the result into
MongoDB.

Usage:
    python Async_Scraper.py               # scrape all stale products
    python Async_Scraper.py --force       # re-scrape everything regardless of age
    python Async_Scraper.py --category processor   # single category

Pipeline:
    1. Bulk_data.py  →  data/*.json  (listing-level data, fast)
    2. Async_Scraper.py  →  MongoDB  (full spec data, slower)
"""
import os
import glob
import json
import asyncio
import logging
import signal
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from pymongo import MongoClient
from curl_cffi.requests import AsyncSession as CurlSession

import common_functions as cf

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
DATA_DIR     = os.path.join(BASE_DIR, "data")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "async_snapshots")
IMAGE_DIR    = os.path.join(BASE_DIR, "product_images")

for _d in (DATA_DIR, SNAPSHOT_DIR, IMAGE_DIR):
    os.makedirs(_d, exist_ok=True)

DB_NAME           = "PC_Parts"
CONNECTION_STRING = "mongodb://localhost:27017/"
FRESHNESS_LIMIT   = timedelta(days=2)

MAX_CONCURRENT = 5
MAX_THREADS    = 5
RETRY_ATTEMPTS = 3
REQUEST_TIMEOUT = 30

# Anti-bot headers
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# Map JSON file prefix → MongoDB collection name
COLLECTION_MAP = {
    "processor":     "Processors",
    "graphics-card": "GPUs",
    "ram":           "RAM",
    "ssd":           "Storage",
    "hdd":           "Storage",     # merged into same collection as SSD
    "motherboard":   "Motherboards",
    "smps":          "SMPS",
    "cabinet":       "Cabinets",
    "cpu-cooler":    "CpuCoolers",
}

_shutdown = False

# ─────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ─────────────────────────────────────────
#  SIGNAL HANDLER
# ─────────────────────────────────────────
def _on_term(signum, frame):
    global _shutdown
    _shutdown = True
    log.warning("Shutdown signal received — will stop after current batch.")

for _sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(_sig, _on_term)
    except (OSError, ValueError):
        pass


# ─────────────────────────────────────────
#  STALENESS CHECK
# ─────────────────────────────────────────
def get_stale_items(collection, products: list[dict], freshness_limit: timedelta) -> list[dict]:
    """Return only products whose DB record is missing or older than freshness_limit."""
    urls = [p["url"] for p in products if p.get("url")]
    if not urls:
        return []

    cutoff     = datetime.now(timezone.utc) - freshness_limit
    fresh_docs = collection.find(
        {"url": {"$in": urls}, "scraped_at": {"$gt": cutoff}},
        {"url": 1},
    )
    fresh_urls = {doc["url"] for doc in fresh_docs}
    return [p for p in products if p.get("url") and p["url"] not in fresh_urls]


# ─────────────────────────────────────────
#  PAGE FETCHER
# ─────────────────────────────────────────
async def fetch_page(session: CurlSession, url: str, retries: int = RETRY_ATTEMPTS) -> str | None:
    """Fetch a page with Chrome TLS impersonation and exponential back-off."""
    for attempt in range(1, retries + 1):
        try:
            resp = await session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (403, 429, 503):
                wait = 2 ** attempt
                log.warning("HTTP %d for %s — attempt %d/%d, waiting %ds",
                            resp.status_code, url, attempt, retries, wait)
                await asyncio.sleep(wait)
                continue
            log.warning("HTTP %d for %s — skipping", resp.status_code, url)
            return None
        except asyncio.TimeoutError:
            log.error("Timeout on %s (attempt %d/%d)", url, attempt, retries)
        except Exception as exc:
            log.error("Error on %s: %s (attempt %d/%d)", url, exc, attempt, retries)
        if attempt < retries:
            await asyncio.sleep(1.5 * attempt)

    log.error("Giving up on %s after %d attempts", url, retries)
    return None


# ─────────────────────────────────────────
#  SNAPSHOT HELPERS
# ─────────────────────────────────────────
def _snapshot_path(url: str) -> str:
    """Stable snapshot filename derived from URL hash."""
    import hashlib
    h = hashlib.md5(url.encode()).hexdigest()[:16]
    return os.path.join(SNAPSHOT_DIR, f"{h}.html")


def _save_snapshot(html: str, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _snapshot_fresh(path: str, limit: timedelta) -> bool:
    if not os.path.exists(path):
        return False
    mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
    return (datetime.now(timezone.utc) - mtime) < limit


# ─────────────────────────────────────────
#  PROCESS ONE PRODUCT (thread-safe)
# ─────────────────────────────────────────
def _parse_and_upsert(snapshot_path: str, product: dict, collection) -> None:
    """Parse a saved HTML snapshot and upsert into MongoDB (runs in thread pool).

    The `product` dict comes from the Bulk_data JSON and already contains
    listing-level price data.  We use that as a fallback layer: if the
    individual-page HTML parse returns a null price field, we fill it in
    from the JSON listing instead.
    """
    try:
        parsed = cf.parse_product_page(
            html_file_path=snapshot_path,
            product_url=product.get("url"),
            image_url=product.get("image_url"),
            collection=collection,
            image_dir=IMAGE_DIR,
        )

        # ── Merge bulk-listing prices as fallback ──
        # The JSON `product` dict has a "price" dict with keys like
        # "original", "discounted", "discount" that are ALWAYS present
        # (from the category listing page).  If parse_product_page
        # failed to extract any of those from the detail-page HTML,
        # fall back to the listing values so we never store an empty price.
        bulk_price = product.get("price", {})
        if isinstance(bulk_price, dict):
            parsed_price = parsed.get("price", {}) or {}

            for key in ("discounted", "original", "discount"):
                if not parsed_price.get(key) and bulk_price.get(key):
                    parsed_price[key] = bulk_price[key]

            parsed["price"] = parsed_price

        cf.upsert_product(collection, parsed)
    except Exception as exc:
        log.error("Parse/upsert failed for %s: %s", product.get("url"), exc)



# ─────────────────────────────────────────
#  ASYNC PRODUCT PROCESSOR
# ─────────────────────────────────────────
async def process_product(
    session: CurlSession,
    product: dict,
    collection,
    executor: ThreadPoolExecutor,
    semaphore: asyncio.Semaphore,
    force: bool = False,
) -> None:
    """Download + parse + upsert a single product page."""
    global _shutdown
    if _shutdown:
        return

    url      = product.get("url")
    snap_path = _snapshot_path(url)

    async with semaphore:
        # Use cached snapshot if still fresh
        if not force and _snapshot_fresh(snap_path, FRESHNESS_LIMIT):
            log.debug("Using cached snapshot for %s", url)
        else:
            html = await fetch_page(session, url)
            if not html:
                return
            _save_snapshot(html, snap_path)

        # Parse + upsert in thread pool (BeautifulSoup is CPU-bound)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor, _parse_and_upsert, snap_path, product, collection
        )

    await asyncio.sleep(0.4)   # polite crawl delay


# ─────────────────────────────────────────
#  CATEGORY RUNNER
# ─────────────────────────────────────────
async def run_category(
    session: CurlSession,
    slug: str,
    collection,
    executor: ThreadPoolExecutor,
    semaphore: asyncio.Semaphore,
    force: bool = False,
) -> int:
    """Scrape all stale products for a given category slug. Returns count processed."""
    # Find matching JSON files
    json_files = glob.glob(os.path.join(DATA_DIR, f"{slug}_*.json"))
    if not json_files:
        log.warning("No JSON data files found for category: %s", slug)
        log.warning("  → Run Bulk_data.py first to populate data/")
        return 0

    # Load products from the newest file
    json_files.sort(key=os.path.getmtime, reverse=True)
    with open(json_files[0], "r", encoding="utf-8") as f:
        products = json.load(f)

    log.info("[%s] Loaded %d products from %s", slug, len(products), Path(json_files[0]).name)

    # Filter to stale products only (unless --force)
    to_process = products if force else get_stale_items(collection, products, FRESHNESS_LIMIT)
    log.info("[%s] %d products need scraping", slug, len(to_process))

    if not to_process:
        return 0

    tasks = [
        asyncio.create_task(
            process_product(session, p, collection, executor, semaphore, force=force)
        )
        for p in to_process
        if p.get("url")
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    return len(to_process)


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
async def main() -> None:
    parser = argparse.ArgumentParser(description="PrimeABGB async product scraper")
    parser.add_argument("--force",    action="store_true", help="Re-scrape all products ignoring freshness")
    parser.add_argument("--category", type=str, default=None,
                        help=f"Scrape only this category slug ({', '.join(COLLECTION_MAP)})")
    args = parser.parse_args()

    client = MongoClient(CONNECTION_STRING)
    db     = client[DB_NAME]

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    slugs_to_run = (
        [args.category] if args.category
        else list(COLLECTION_MAP.keys())
    )
    # Validate
    for slug in slugs_to_run:
        if slug not in COLLECTION_MAP:
            log.error("Unknown category slug: %s. Valid: %s", slug, list(COLLECTION_MAP))
            sys.exit(1)

    log.info("PrimeABGB Async Scraper — %d categories, force=%s", len(slugs_to_run), args.force)

    total_processed = 0
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        async with CurlSession(impersonate="chrome", headers=HEADERS) as session:
            for slug in slugs_to_run:
                if _shutdown:
                    break
                coll_name  = COLLECTION_MAP[slug]
                collection = db[coll_name]
                count = await run_category(
                    session, slug, collection, executor, semaphore, force=args.force
                )
                total_processed += count
                log.info("[%s] Done — %d products processed", slug, count)

    log.info("All done — %d products processed in total.", total_processed)
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
