# --- Async_Scraper.py ---
import os
import json
import glob
import asyncio
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient
import aiohttp
from concurrent.futures import ThreadPoolExecutor

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

            # Upsert to MongoDB (blocking I/O)
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
# Main orchestration
# -----------------------------
async def main():
    loop = asyncio.get_running_loop()
    executor = ThreadPoolExecutor(max_workers=MAX_THREADS)
    loop.set_default_executor(executor)

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    # ---------------- Load JSONs ----------------
    all_json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not all_json_files:
        print(f"No JSON files found in {DATA_DIR}.")
        return

    print("\n📦 Available JSON data files:")
    for i, file in enumerate(all_json_files, 1):
        print(f"{i}. {Path(file).stem.replace('_', ' ').capitalize()}")

    raw_choice = cf.input_with_timeout(
        "\nEnter the number of the file to process (blank = ALL)", timeout=10
    )
    choice = (raw_choice or "").strip()

    if choice and choice.isdigit() and 1 <= int(choice) <= len(all_json_files):
        files_to_process = [all_json_files[int(choice) - 1]]
    else:
        files_to_process = all_json_files

    # ---------------- Mapping ----------------
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

    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        for file_path in files_to_process:
            base_name = Path(file_path).stem.split("_")[0].lower()
            collection_name = mapping.get(base_name, base_name.capitalize())
            collection = db[collection_name]

            print(f"\n📂 Processing: {os.path.basename(file_path)} → Collection: {collection_name}")

            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)

            # ---------------- Filter stale items ----------------
            stale_items = []
            for item in products:
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

            if not stale_items:
                print("All products are up to date.")
                continue

            print(f"🌐 Downloading {len(stale_items)} snapshots concurrently...")

            # ---------------- Async download snapshots ----------------
            download_tasks = [
                cf.download_with_retry(
                    session, item["url"], SNAPSHOT_DIR, prefix=base_name, retries=RETRY_ATTEMPTS
                )
                for item in stale_items
            ]
            snapshots = await asyncio.gather(*download_tasks)

            # ---------------- Parse + DB upserts ----------------
            tasks = []
            failed_items = []
            for item, snap_path in zip(stale_items, snapshots):
                if not snap_path:
                    failed_items.append(item)
                    continue
                item["snapshot_path"] = snap_path
                tasks.append(
                    asyncio.create_task(
                        process_product_async(loop, semaphore, db, collection_name, item)
                    )
                )

            print(f"🚀 Running {len(tasks)} async parse + DB update tasks...")
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                completed += 1
                print(f"{result}  ({completed}/{len(tasks)} done)")

            # ---------------- Retry Failed Items ----------------
            if failed_items:
                print(f"\n🔁 Retrying {len(failed_items)} failed downloads...\n")
                retry_downloads = [
                    cf.download_with_retry(
                        session, item["url"], SNAPSHOT_DIR, prefix=base_name, retries=5
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
                        result = await coro
                        completed += 1
                        print(f"{result}  (retry {completed}/{len(retry_tasks)} done)")
                    print("✅ Retry batch complete.\n")

            print(f"\n✅ Finished file: {os.path.basename(file_path)}\n")

    # ---------------- Cleanup ----------------
    print("\n🧹 Cleaning up snapshot files...")
    cleanup_tasks = [
        asyncio.to_thread(os.remove, os.path.join(SNAPSHOT_DIR, f))
        for f in os.listdir(SNAPSHOT_DIR)
        if f.endswith(".html")
    ]
    await asyncio.gather(*cleanup_tasks, return_exceptions=True)
    print("🧾 Cleanup complete.")

    # ---------------- Async cleanup of non-internal drives ----------------
    await cf.async_remove_non_internal_storage(CONNECTION_STRING, DB_NAME)
    print("\n🎉 All selected JSON files processed successfully!\n")


if __name__ == "__main__":
    asyncio.run(main())
