import os
import json
import glob
import asyncio
import random
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from pymongo import MongoClient

import common_functions as cf
from Individual_Data import parse_product_page, input_with_timeout  # reuse existing functions

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SNAPSHOT_DIR = os.path.join(BASE_DIR, "async_snapshots")
IMAGE_DIR = os.path.join(BASE_DIR, "product_images")

os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

DB_NAME = "PC_Parts"
CONNECTION_STRING = "mongodb://localhost:27017/"
FRESHNESS_LIMIT = timedelta(days=2)  # skip if scraped < 2 days ago


# --- Async Mongo Update Task ---
# --- Async Mongo Update Task ---
async def process_product_async(loop, semaphore, collection_name, product_item):
    """
    Async task: parses HTML (threaded) + updates MongoDB (threaded).
    Includes logic to skip or remove non-internal storage drives.
    """
    async with semaphore:
        url = product_item["url"]
        image_url = product_item.get("image_url")

        try:
            # Parse in executor (BeautifulSoup is blocking)
            product_data = await loop.run_in_executor(
                None, parse_product_page,
                product_item["snapshot_path"], url, image_url, None
            )

            # --- Skip non-internal storage ---
            if collection_name.lower() == "storage":
                specs_text = " ".join(
                    [f"{k} {v}".lower() for k, v in product_data.get("specifications", {}).items()]
                )
                if "internal" not in specs_text:
                    print(f"⏩ Skipping Non-Internal Storage: {product_data['name']}")
                    # Remove from DB if already exists
                    await loop.run_in_executor(
                        None,
                        lambda: MongoClient(CONNECTION_STRING)[DB_NAME][collection_name].delete_one({"url": url})
                    )
                    return f"🗑️ Removed non-internal storage: {product_data['name']}"

            # --- Save to Mongo in executor ---
            await loop.run_in_executor(
                None, cf.upsert_product,
                product_data, CONNECTION_STRING, DB_NAME, collection_name
            )

            return f"✅ Processed: {product_data['name']}"

        except Exception as e:
            return f"❌ Error processing {url}: {e}"



async def main():
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(6)
    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    # --- Load available JSON files ---
    all_json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not all_json_files:
        print(f"No JSON files found in {DATA_DIR}.")
        return

    print("\n📦 Available JSON data files:")
    for i, file in enumerate(all_json_files, 1):
        print(f"{i}. {os.path.basename(file)}")

    choice = input_with_timeout(
        "\nEnter the number of the file to process (blank = ALL)",
        timeout=10
    ).strip()

    if choice and choice.isdigit() and 1 <= int(choice) <= len(all_json_files):
        files_to_process = [all_json_files[int(choice) - 1]]
        print(f"\n📁 Selected file: {os.path.basename(files_to_process[0])}")
    else:
        files_to_process = all_json_files
        print("\n📁 Processing all JSON files...")

    # --- Mapping for collections ---
    mapping = {
        "graphics-card": "GPUs",
        "processor": "Processors",
        "ram": "RAM",
        "motherboard": "Motherboards",
        "smps": "SMPS",
        "storage": "Storage",
        "cabinet": "Cabinets",
        "cpu-cooler": "CpuCoolers"
    }

    try:
        for file_path in files_to_process:
            base_name = Path(file_path).stem.split("_")[0].lower()
            collection_name = mapping.get(base_name, base_name.capitalize())
            collection = db[collection_name]

            print(f"\n📂 Processing: {os.path.basename(file_path)} → Collection: {collection_name}")
            with open(file_path, "r", encoding="utf-8") as f:
                products = json.load(f)

            tasks = []
            for item in products:
                url = item.get("url")
                image_url = item.get("image_url")
                if not url:
                    continue

                # --- Check if record is fresh in DB ---
                existing = collection.find_one({"url": url}, {"scraped_at": 1, "name": 1})
                if existing and existing.get("scraped_at"):
                    try:
                        scraped_at = datetime.fromisoformat(existing["scraped_at"])
                        age = datetime.now(timezone.utc) - scraped_at
                        if age < FRESHNESS_LIMIT:
                            hours = age.seconds // 3600
                            mins = (age.seconds % 3600) // 60
                            time_str = f"{age.days}d {hours}h {mins}m ago" if age.days else f"{hours}h {mins}m ago"
                            print(f"⏩ Skipping (fresh: {time_str}): {existing.get('name', url)}")
                            continue
                    except Exception:
                        pass

                # --- Download snapshot synchronously ---
                try:
                    html_file = cf.save_snapshot(url, SNAPSHOT_DIR, prefix="mdcomputers")
                    item["snapshot_path"] = html_file
                except Exception as e:
                    print(f"⚠️ Failed to download {url}: {e}")
                    continue

                # --- Schedule async parsing/upsert ---
                task = asyncio.create_task(
                    process_product_async(loop, semaphore, collection_name, item)
                )
                tasks.append(task)
                await asyncio.sleep(random.uniform(1.0, 2.0))  # throttle fetches

            # --- Run async tasks per file with progress tracking ---
            if tasks:
                total = len(tasks)
                print(f"\n🚀 Running {total} async parse + DB update tasks for {os.path.basename(file_path)}...\n")

                completed = 0
                for coro in asyncio.as_completed(tasks):
                    result = await coro
                    completed += 1
                    print(f"{result}  ({completed}/{total} completed)")

                tasks.clear()

            print(f"\n✅ Completed processing file: {os.path.basename(file_path)}\n")

        print("\n🎉 All selected JSON files processed successfully!\n")

    except asyncio.CancelledError:
        print("⚠️ Cancelled by user.")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    finally:
        # --- Cleanup snapshots ---
        print("\n🧹 Cleaning up snapshot files...")
        for file in os.listdir(SNAPSHOT_DIR):
            try:
                os.remove(os.path.join(SNAPSHOT_DIR, file))
            except Exception:
                pass
        print("🧾 Cleanup complete.")


if __name__ == "__main__":
    asyncio.run(main())
