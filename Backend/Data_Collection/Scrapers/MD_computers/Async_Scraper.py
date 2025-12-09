import os
import json
import glob
import asyncio
import random
import signal
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient
import aiohttp
from concurrent.futures import ThreadPoolExecutor
from fake_useragent import UserAgent
import argparse
import common_functions as cf

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "async_snapshots")
IMAGE_DIR = os.path.join(BASE_DIR, "product_images")

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

DB_NAME = "PC_Parts"
CONNECTION_STRING = "mongodb://localhost:27017/"
FRESHNESS_LIMIT = timedelta(days=2)

DEBUG = True
MAX_CONCURRENT_DOWNLOADS = 25
MAX_THREADS = 12
RETRY_ATTEMPTS = 3

_shutdown = False


def _on_term(signum, frame):
    global _shutdown
    _shutdown = True
    print("\nReceived shutdown signal, will stop after current item...")


# -----------------------------
# Async product processor
# -----------------------------
async def process_product_async(loop, semaphore, db, collection_name, product_item):
    """Parse saved snapshot, then upsert into MongoDB."""
    async with semaphore:
        url = product_item.get("url")
        image_url = product_item.get("image_url")
        snapshot_path = product_item.get("snapshot_path")

        try:
            # Parse product page (CPU-bound, so run in thread pool)
            product_data = await loop.run_in_executor(
                None,
                cf.parse_product_page,
                snapshot_path,
                url,
                image_url,
                db[collection_name],
            )

            # Ensure we store collection name on upsert call
            await loop.run_in_executor(
                None,
                cf.upsert_product,
                product_data,
                CONNECTION_STRING,
                DB_NAME,
                collection_name,
            )

            if DEBUG:
                print(f"✅ Processed: {product_data.get('name', url)}")
            return f"✅ {url}"

        except Exception as e:
            if DEBUG:
                print(f"❌ Error processing {url}: {e}")
            return f"❌ {url}: {e}"

        finally:
            # Cleanup snapshot safely
            if snapshot_path and os.path.exists(snapshot_path):
                try:
                    os.remove(snapshot_path)
                except Exception as e:
                    if DEBUG:
                        print(f"⚠️ Could not remove snapshot {snapshot_path}: {e}")


# -----------------------------
# Core runner (headless) - processes given file paths
# -----------------------------
async def run_files(file_paths, limit=None, dry_run=False):
    """Process a list of snapshot JSON files (absolute or relative paths).

    Args:
        file_paths: iterable of file path strings to JSON snapshots
        limit: optional int, maximum items to process per file
        dry_run: if True, will not upsert to DB (parsing only)
    """
    global _shutdown

    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
    loop.set_default_executor(executor)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    mapping = {
        "graphics-card": "GPUs",
        "processor": "Processors",
        "ram": "RAM",
        "motherboard": "Motherboards",
        "smps": "SMPS",
        "storage": "Storage",
        "cabinet": "Cabinets",
        "cpu-cooler": "CpuCoolers",
    }

    # safe fake-useragent usage with fallback
    try:
        ua = UserAgent()
        ua_string = ua.random
    except Exception:
        ua_string = cf.DEFAULT_USER_AGENT if hasattr(cf, 'DEFAULT_USER_AGENT') else "Mozilla/5.0"

    headers = {"User-Agent": ua_string}

    async with aiohttp.ClientSession(headers=headers) as session:
        for file_path in file_paths:
            if _shutdown:
                print("Shutdown requested — stopping before starting next file.")
                break

            file_path = str(file_path)
            if not os.path.exists(file_path):
                print(f"⚠️ File not found: {file_path}")
                continue

            base_name = Path(file_path).stem.split("_")[0].lower()
            collection_name = mapping.get(base_name, base_name.capitalize())
            collection = db[collection_name]

            print(f"\n📂 Processing: {os.path.basename(file_path)} → Collection: {collection_name}")

            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)

            if limit:
                products = products[:limit]

            # ---------------- Filter stale items ----------------
            stale_items = []
            for item in products:
                if _shutdown:
                    break
                url = item.get("url")
                if not url:
                    continue

                existing = collection.find_one({"url": url}, {"scraped_at": 1, "name": 1})
                if existing and existing.get("scraped_at"):
                    scraped_at_raw = existing["scraped_at"]
                    scraped_at = scraped_at_raw if isinstance(scraped_at_raw, datetime) else None
                    if not scraped_at:
                        try:
                            scraped_at = datetime.fromisoformat(str(scraped_at_raw))
                        except Exception:
                            pass

                    if scraped_at:
                        if scraped_at.tzinfo is None:
                            scraped_at = scraped_at.replace(tzinfo=timezone.utc)
                        age = datetime.now(timezone.utc) - scraped_at
                        if age < FRESHNESS_LIMIT:
                            if DEBUG:
                                print(f"⏩ Skipping fresh: {existing.get('name', url)}")
                            continue
                stale_items.append(item)

            if _shutdown:
                print("Shutdown requested — aborting processing of current file.")
                break

            if not stale_items:
                print("All products are up to date.")
                continue

            print(f"🌐 Downloading {len(stale_items)} snapshots concurrently...")

            # ---------------- Async download snapshots ----------------
            download_tasks = []
            for item in stale_items:
                u = item.get("url")
                if not u:
                    download_tasks.append(asyncio.sleep(0, result=None))
                else:
                    download_tasks.append(
                        cf.download_with_retry(
                            session, u, SNAPSHOT_DIR, prefix=base_name, retries=RETRY_ATTEMPTS
                        )
                    )

            try:
                snapshots = await asyncio.gather(*download_tasks)
            except Exception as e:
                print(f"❌ Error during snapshot downloads: {e}")
                snapshots = [None] * len(download_tasks)

            # ---------------- Parse + DB upserts ----------------
            tasks = []
            failed_items = []
            for item, snap_path in zip(stale_items, snapshots):
                if _shutdown:
                    break
                if not snap_path:
                    failed_items.append(item)
                    continue
                item["snapshot_path"] = snap_path
                if dry_run:
                    # Do lightweight parse in thread pool but skip DB upsert
                    async def _dry_parse(loop, snap, url, image_url):
                        try:
                            parsed = await loop.run_in_executor(
                                None, cf.parse_product_page, snap, url, image_url, None
                            )
                            print(f"(DRY) Parsed: {parsed.get('name', url)}")
                        except Exception as e:
                            print(f"(DRY) Error parsing {url}: {e}")

                    tasks.append(
                        asyncio.create_task(_dry_parse(loop, snap_path, item.get("url"), item.get("image_url")))
                    )
                else:
                    tasks.append(
                        asyncio.create_task(
                            process_product_async(loop, semaphore, db, collection_name, item)
                        )
                    )

            if _shutdown:
                print("Shutdown requested — waiting for already-running item tasks to finish...")

            print(f"🚀 Running {len(tasks)} async parse + DB update tasks...")
            completed = 0
            for coro in asyncio.as_completed(tasks):
                try:
                    result = await coro
                except Exception as e:
                    result = f"❌ Task error: {e}"
                completed += 1
                print(f"{result}  ({completed}/{len(tasks)} done)")

            # ---------------- Retry Failed Items ----------------
            if failed_items and not _shutdown:
                print(f"\n🔁 Retrying {len(failed_items)} failed downloads...\n")
                retry_downloads = [
                    cf.download_with_retry(
                        session, item.get("url"), SNAPSHOT_DIR, prefix=base_name, retries=5
                    )
                    for item in failed_items
                ]
                retry_snapshots = await asyncio.gather(*retry_downloads)

                retry_tasks = []
                for item, snap_path in zip(failed_items, retry_snapshots):
                    if not snap_path:
                        print(f"❌ Still failed after retry: {item.get('url')}")
                        continue
                    item["snapshot_path"] = snap_path
                    retry_tasks.append(
                        asyncio.create_task(
                            process_product_async(loop, semaphore, db, collection_name, item)
                        )
                    )

                if retry_tasks:
                    print(f"🚀 Reprocessing {len(retry_tasks)} retried products...")
                    completed = 0
                    for coro in asyncio.as_completed(retry_tasks):
                        try:
                            result = await coro
                        except Exception as e:
                            result = f"❌ Retry task error: {e}"
                        completed += 1
                        print(f"{result}  (retry {completed}/{len(retry_tasks)} done)")
                    print("✅ Retry batch complete.\n")

            print(f"\n✅ Finished file: {os.path.basename(file_path)}\n")

            # polite sleep between files
            await asyncio.sleep(random.uniform(0.4, 1.0))

            if _shutdown:
                print("Shutdown requested — exiting main loop.")
                break

    # ---------------- Cleanup ----------------
    print("\n🧹 Cleaning up snapshot files...")
    try:
        cleanup_tasks = [
            asyncio.to_thread(os.remove, os.path.join(SNAPSHOT_DIR, f))
            for f in os.listdir(SNAPSHOT_DIR)
            if f.endswith(".html") and os.path.exists(os.path.join(SNAPSHOT_DIR, f))
        ]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    except Exception as e:
        print(f"Error during cleanup: {e}")
    print("🧾 Cleanup complete.")

    #-----------------Recover Missing Images---------------
    try:
        await cf.async_recover_missing_images(CONNECTION_STRING, DB_NAME, IMAGE_DIR)
    except Exception as e:
        print(f"Error recovering images: {e}")

    # ---------------- Async cleanup of non-internal drives ----------------
    try:
        await cf.async_remove_non_internal_storage(CONNECTION_STRING, DB_NAME)
    except Exception as e:
        print(f"Error during storage cleanup: {e}")

    print("\n🎉 All selected JSON files processed successfully!\n")


# -----------------------------
# CLI wrapper: argparse + graceful shutdown
# -----------------------------
def cli_entry():
    parser = argparse.ArgumentParser(description="MD_computers async scraper (headless)")
    parser.add_argument("--file", "-f", help="JSON filename inside data/ to process (e.g. md_computers_2025-12-08.json)")
    parser.add_argument("--all", action="store_true", help="Process all JSON files in data/")
    parser.add_argument("--limit", type=int, default=None, help="Limit items per file")
    parser.add_argument("--dry", dest="dry", action="store_true", help="Dry run: parse only, no DB upserts")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _on_term)
    signal.signal(signal.SIGTERM, _on_term)

    if args.all:
        files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    elif args.file:
        files = [os.path.join(DATA_DIR, args.file)]
    else:
        # default: process all files
        files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))

    if not files:
        print(f"No JSON files found in {DATA_DIR} to process.")
        return

    try:
        asyncio.run(run_files(files, limit=args.limit, dry_run=args.dry))
    except Exception as e:
        print(f"Fatal error during run: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_entry()
