import os
import json
import glob
import asyncio
import logging
import random
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient
from curl_cffi.requests import AsyncSession as CurlSession  # replaces aiohttp for page fetches
import aiohttp   # kept only for REQUEST_TIMEOUT type used in cf.download_with_retry
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
import argparse
import common_functions as cf

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "async_snapshots")
IMAGE_DIR = os.path.join(BASE_DIR, "product_images")

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

DB_NAME           = "PC_Parts"
CONNECTION_STRING = "mongodb://localhost:27017/"
FRESHNESS_LIMIT   = timedelta(days=2)

MAX_CONCURRENT_DOWNLOADS = 25
MAX_THREADS      = 12
RETRY_ATTEMPTS   = 3
REQUEST_TIMEOUT  = 30   # seconds — plain int for curl_cffi (not aiohttp.ClientTimeout)

# FIX: moved to module level so it's easy to extend without touching async logic
COLLECTION_MAP = {
    "graphics-card": "GPUs",
    "processor":     "Processors",
    "ram":           "RAM",
    "motherboard":   "Motherboards",
    "smps":          "SMPS",
    "storage":       "Storage",
    "cabinet":       "Cabinets",
    "cpu-cooler":    "CpuCoolers",
}

_shutdown = False

# ─────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Suppress noisy third-party debug logs (pymongo topology, urllib3 requests)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ─────────────────────────────────────────
#  SIGNAL HANDLER
# ─────────────────────────────────────────
def _on_term(signum, frame):
    global _shutdown
    _shutdown = True
    log.warning("Received shutdown signal — will stop after current batch.")


# ─────────────────────────────────────────
#  BULK STALENESS CHECK  (FIX: was N sequential find_one calls)
# ─────────────────────────────────────────
def get_stale_items(collection, products, freshness_limit: timedelta) -> list:
    """
    Return only items whose DB record is missing or older than freshness_limit.
    Uses a single bulk query instead of one find_one per product.
    """
    urls = [item["url"] for item in products if item.get("url")]
    if not urls:
        return []

    cutoff = datetime.now(timezone.utc) - freshness_limit

    # One round-trip to MongoDB for all URLs
    fresh_docs = collection.find(
        {"url": {"$in": urls}, "scraped_at": {"$gt": cutoff}},
        {"url": 1},
    )
    fresh_urls = {doc["url"] for doc in fresh_docs}

    stale = []
    for item in products:
        url = item.get("url")
        if not url:
            continue
        if url in fresh_urls:
            log.debug("⏩ Skipping fresh: %s", url)
        else:
            stale.append(item)

    return stale


# ─────────────────────────────────────────
#  DRY-RUN HELPER  (FIX: defined outside loop — no closure/late-binding bug)
# ─────────────────────────────────────────
async def _dry_parse(loop: asyncio.AbstractEventLoop, snap: str, url: str, image_url: str | None):
    """Parse a snapshot without writing to the DB. Cleans up the snapshot file."""
    try:
        parsed = await loop.run_in_executor(
            None, cf.parse_product_page, snap, url, image_url, None
        )
        log.info("(DRY) Parsed: %s", parsed.get("name", url))
    except Exception as exc:
        log.error("(DRY) Error parsing %s: %s", url, exc)
    finally:
        # FIX: dry-run now also cleans up snapshot files
        if snap and os.path.exists(snap):
            try:
                os.remove(snap)
            except OSError as exc:
                log.warning("⚠️  Could not remove snapshot %s: %s", snap, exc)


# ─────────────────────────────────────────
#  ASYNC PRODUCT PROCESSOR
# ─────────────────────────────────────────
async def process_product_async(
    loop: asyncio.AbstractEventLoop,
    semaphore: asyncio.Semaphore,
    db,
    collection_name: str,
    product_item: dict,
) -> str:
    """Parse saved snapshot, then upsert into MongoDB."""
    async with semaphore:
        url          = product_item.get("url")
        image_url    = product_item.get("image_url")
        snapshot_path = product_item.get("snapshot_path")

        try:
            product_data = await loop.run_in_executor(
                None,
                cf.parse_product_page,
                snapshot_path,
                url,
                image_url,
                db[collection_name],
            )

            await loop.run_in_executor(
                None,
                cf.upsert_product,
                product_data,
                CONNECTION_STRING,
                DB_NAME,
                collection_name,
            )

            log.debug("✅ Processed: %s", product_data.get("name", url))
            return url

        except Exception as exc:
            log.error("❌ Error processing %s: %s", url, exc)
            return f"❌ {url}: {exc}"

        finally:
            if snapshot_path and os.path.exists(snapshot_path):
                try:
                    os.remove(snapshot_path)
                except OSError as exc:
                    log.warning("⚠️  Could not remove snapshot %s: %s", snapshot_path, exc)


# ─────────────────────────────────────────
#  BATCH RUNNER
# ─────────────────────────────────────────
async def _run_batch(
    loop: asyncio.AbstractEventLoop,
    semaphore: asyncio.Semaphore,
    session: CurlSession,
    db,
    collection,
    collection_name: str,
    stale_items: list,
    base_name: str,
    dry_run: bool,
) -> list:
    """
    Download snapshots for stale_items, then parse+upsert (or dry-parse).
    Returns items whose downloads failed for retry.
    """
    global _shutdown

    log.info("🌐 Downloading %d snapshots concurrently…", len(stale_items))

    download_coros = [
        cf.download_with_retry(session, item["url"], SNAPSHOT_DIR, prefix=base_name, retries=RETRY_ATTEMPTS)
        if item.get("url")
        else asyncio.sleep(0, result=None)
        for item in stale_items
    ]

    # FIX: wrap gather so we can cancel on shutdown
    gather_task = asyncio.ensure_future(asyncio.gather(*download_coros, return_exceptions=True))
    try:
        snapshots = await gather_task
    except asyncio.CancelledError:
        log.warning("Download batch cancelled.")
        return []

    if _shutdown:
        gather_task.cancel()
        return []

    tasks        = []
    failed_items = []

    for item, snap_path in zip(stale_items, snapshots):
        if _shutdown:
            break
        # download_with_retry may return an exception object when return_exceptions=True
        if isinstance(snap_path, Exception) or not snap_path:
            failed_items.append(item)
            continue

        item["snapshot_path"] = snap_path

        if dry_run:
            tasks.append(
                asyncio.create_task(
                    _dry_parse(loop, snap_path, item.get("url"), item.get("image_url"))
                )
            )
        else:
            tasks.append(
                asyncio.create_task(
                    process_product_async(loop, semaphore, db, collection_name, item)
                )
            )

    if tasks:
        log.info("🚀 Running %d async tasks…", len(tasks))
        completed = 0
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
            except Exception as exc:
                result = f"❌ Task error: {exc}"
            completed += 1
            log.info("%s  (%d/%d done)", result, completed, len(tasks))

    return failed_items


# ─────────────────────────────────────────
#  MAIN ASYNC ENTRY POINT
# ─────────────────────────────────────────
async def run_files(file_paths, limit: int | None = None, dry_run: bool = False):
    """
    Process a list of snapshot JSON files.

    Args:
        file_paths: iterable of file path strings to JSON snapshots
        limit:      optional int — max items to process per file
        dry_run:    if True, parse only — no DB writes
    """
    global _shutdown

    loop     = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
    loop.set_default_executor(executor)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)

    # FIX: MongoClient is now explicitly closed in the finally block
    client = MongoClient(CONNECTION_STRING)
    db     = client[DB_NAME]

    # FIX: CurlSession impersonates Chrome's TLS fingerprint — prevents 403 from
    # Cloudflare/WAF bot filters that aiohttp triggered on every request.
    try:
        async with CurlSession(impersonate="chrome") as session:
            for file_path in file_paths:
                if _shutdown:
                    log.warning("Shutdown requested — stopping before next file.")
                    break

                file_path = str(file_path)
                if not os.path.exists(file_path):
                    log.warning("⚠️  File not found: %s", file_path)
                    continue

                base_name       = Path(file_path).stem.split("_")[0].lower()
                collection_name = COLLECTION_MAP.get(base_name, base_name.capitalize())
                collection      = db[collection_name]

                log.info("📂 Processing: %s → Collection: %s",
                         os.path.basename(file_path), collection_name)

                with open(file_path, "r", encoding="utf-8") as fh:
                    products = json.load(fh)

                if limit:
                    products = products[:limit]

                # ── Bulk staleness filter ──────────────────────────────────
                stale_items = get_stale_items(collection, products, FRESHNESS_LIMIT)

                if _shutdown:
                    log.warning("Shutdown requested — aborting current file.")
                    break

                if not stale_items:
                    log.info("All products are up to date.")
                    continue

                # ── First-pass download + process ──────────────────────────
                failed_items = await _run_batch(
                    loop, semaphore, session, db,
                    collection, collection_name,
                    stale_items, base_name, dry_run,
                )

                # ── Retry failed downloads ─────────────────────────────────
                if failed_items and not _shutdown:
                    log.info("🔁 Retrying %d failed downloads…", len(failed_items))
                    retry_coros = [
                        cf.download_with_retry(
                            session, item["url"], SNAPSHOT_DIR,
                            prefix=base_name, retries=5,
                        )
                        for item in failed_items
                        if item.get("url")
                    ]
                    retry_snapshots = await asyncio.gather(*retry_coros, return_exceptions=True)

                    retry_tasks = []
                    for item, snap_path in zip(failed_items, retry_snapshots):
                        if isinstance(snap_path, Exception) or not snap_path:
                            log.error("❌ Still failed after retry: %s", item.get("url"))
                            continue
                        item["snapshot_path"] = snap_path
                        if dry_run:
                            retry_tasks.append(
                                asyncio.create_task(
                                    _dry_parse(loop, snap_path, item.get("url"), item.get("image_url"))
                                )
                            )
                        else:
                            retry_tasks.append(
                                asyncio.create_task(
                                    process_product_async(loop, semaphore, db, collection_name, item)
                                )
                            )

                    if retry_tasks:
                        log.info("🚀 Reprocessing %d retried products…", len(retry_tasks))
                        completed = 0
                        for coro in asyncio.as_completed(retry_tasks):
                            try:
                                result = await coro
                            except Exception as exc:
                                result = f"❌ Retry error: {exc}"
                            completed += 1
                            log.info("%s  (retry %d/%d done)", result, completed, len(retry_tasks))
                        log.info("✅ Retry batch complete.")

                log.info("✅ Finished file: %s", os.path.basename(file_path))

                # polite inter-file sleep
                await asyncio.sleep(random.uniform(0.4, 1.0))

                if _shutdown:
                    log.warning("Shutdown requested — exiting main loop.")
                    break

    finally:
        # ── Cleanup leftover snapshots ─────────────────────────────────────
        log.info("🧹 Cleaning up snapshot files…")
        try:
            leftover = [
                os.path.join(SNAPSHOT_DIR, f)
                for f in os.listdir(SNAPSHOT_DIR)
                if f.endswith(".html")
            ]
            cleanup_tasks = [asyncio.to_thread(os.remove, p) for p in leftover if os.path.exists(p)]
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        except Exception as exc:
            log.error("Error during cleanup: %s", exc)
        log.info("🧾 Cleanup complete.")

        # ── Recover missing images ─────────────────────────────────────────
        try:
            await cf.async_recover_missing_images(CONNECTION_STRING, DB_NAME, IMAGE_DIR)
        except Exception as exc:
            log.error("Error recovering images: %s", exc)

        # ── Remove non-internal storage entries ────────────────────────────
        try:
            await cf.async_remove_non_internal_storage(CONNECTION_STRING, DB_NAME)
        except Exception as exc:
            log.error("Error during storage cleanup: %s", exc)

        # FIX: always close the MongoClient
        client.close()

    log.info("____ All selected JSON files processed successfully! ____")


# ─────────────────────────────────────────
#  FILE SELECTION HELPER
# ─────────────────────────────────────────
def _select_files(files: list[str]) -> list[str]:
    """Interactively prompt the user to pick one file or all."""
    print("\n" + "-" * 40)
    print("   AVAILABLE SNAPSHOT FILES")
    print("-" * 40)
    for i, f in enumerate(files, 1):
        print(f"  {i}. {os.path.basename(f)}")
    print(f"  {len(files) + 1}. PROCESS ALL FILES (default)")
    print("-" * 40 + "\n")

    choice = cf.input_with_timeout("Select a file by number", timeout=10)

    if not choice.strip():
        print(">> No input — auto-selecting ALL files.")
        return files

    try:
        sel = int(choice.strip())
        if 1 <= sel <= len(files):
            print(f">> Selected: {os.path.basename(files[sel - 1])}")
            return [files[sel - 1]]
        elif sel == len(files) + 1:
            print(">> Selected: ALL FILES")
            return files
        else:
            print(">> Invalid number — defaulting to ALL files.")
            return files
    except ValueError:
        print(">> Invalid input — defaulting to ALL files.")
        return files


# ─────────────────────────────────────────
#  CLI ENTRY POINT  (FIX: argparse now actually wired up)
# ─────────────────────────────────────────
def cli_entry():
    signal.signal(signal.SIGINT,  _on_term)
    signal.signal(signal.SIGTERM, _on_term)

    # FIX: --dry-run and --limit are now real CLI flags
    parser = argparse.ArgumentParser(
        description="Async PC-parts scraper — downloads, parses, and upserts product data."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse snapshots without writing to MongoDB.",
    )
    parser.add_argument(
        "--limit", type=int, default=None, metavar="N",
        help="Process only the first N products per file.",
    )
    parser.add_argument(
        "--file", type=str, default=None, metavar="FILENAME",
        help="Process a specific JSON filename in the data directory.",
    )
    args = parser.parse_args()

    all_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not all_files:
        log.error("No JSON files found in %s.", DATA_DIR)
        sys.exit(1)

    # If --file was passed, skip interactive prompt
    if args.file:
        target = os.path.join(DATA_DIR, args.file)
        if not os.path.exists(target):
            log.error("File not found: %s", target)
            sys.exit(1)
        selected = [target]
        log.info("Using --file: %s", args.file)
    else:
        selected = _select_files(all_files)

    if not selected:
        return

    if args.dry_run:
        log.info("*** DRY-RUN MODE — no DB writes ***")

    log.info("Starting pipeline for %d file(s)…", len(selected))

    try:
        asyncio.run(run_files(selected, limit=args.limit, dry_run=args.dry_run))
    except Exception as exc:
        log.critical("Fatal error during run: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli_entry()