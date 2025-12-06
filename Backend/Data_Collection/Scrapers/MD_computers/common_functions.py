# --- common_functions.py ---
import os
import json
import requests
import hashlib
import threading
import queue
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Set, Dict, Any
from pymongo import MongoClient
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import aiohttp
import asyncio

# Configuration defaults
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; Scraper/1.0)"
MAX_FILENAME_LENGTH = 150
MAX_HTML_SIZE = 2_000_000  # 2 MB limit (truncate if larger)
DEFAULT_ASYNC_TIMEOUT = 30  # seconds


# Utilities
def safe_filename(name: str) -> str:
    """
    Sanitize string to make it a valid filename across platforms.
    Removes or replaces characters not allowed on Windows and trims length.
    """
    if not name:
        return ""
    # replace scheme and control characters first
    s = name.replace("https://", "").replace("http://", "")
    # replace forbidden characters for filenames: \ / : * ? " < > |
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    # normalize whitespace to single underscores
    s = re.sub(r"\s+", "_", s)
    # trim length
    if len(s) > MAX_FILENAME_LENGTH:
        s = s[:MAX_FILENAME_LENGTH]
    return s


def slugify(url: str) -> str:
    """Compatibility wrapper for older code; uses safe_filename internally."""
    return safe_filename(url)


def content_hash(content: bytes | str) -> str:
    """Create an MD5 hash for deduplication (works on bytes or str)."""
    h = hashlib.md5()
    if isinstance(content, str):
        content = content.encode("utf-8")
    h.update(content)
    return h.hexdigest()


# JSON / file helpers
def save_json(data: Any, folder: str, prefix: str = "data") -> str:
    """
    Save data to a timestamped JSON file (yyyy-mm-dd).
    Deletes old JSON files starting with the same prefix older than 2 days.
    Returns the path saved.
    """
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).date()

    # Cleanup old files
    for filename in os.listdir(folder):
        if filename.endswith(".json") and filename.startswith(prefix):
            try:
                date_str = filename.rsplit("_", 1)[-1].replace(".json", "")
                try:
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                except Exception:
                    continue
                if (today - file_date).days > 2:
                    try:
                        os.remove(os.path.join(folder, filename))
                        # small print for debug — can be silenced by caller
                        print(f"🗑️ Deleting old file: {filename}")
                    except Exception:
                        pass
            except Exception:
                pass

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{prefix}_{timestamp}.json"
    filepath = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


# Snapshot downloaders
def save_snapshot(url: str, folder: str, prefix: str = "", page: Optional[int] = None,
                  timeout: int = 20, user_agent: str = DEFAULT_USER_AGENT,
                  max_size: int = MAX_HTML_SIZE) -> Optional[str]:
    """
    Synchronous snapshot saver using `requests`.
    Returns filepath or None on failure.
    """
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra = f"_p{page}" if page else ""
    slug = safe_filename(url)
    filename = f"{prefix}_{today}{extra}_{slug}.html"
    filepath = os.path.join(folder, filename)

    try:
        resp = requests.get(url, headers={"User-Agent": UserAgent().random if UserAgent else user_agent},
                            timeout=timeout)
        resp.raise_for_status()
        text = resp.text
        if max_size and len(text) > max_size:
            text = text[:max_size]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to save snapshot for {url}: {e}")
        return None


async def async_save_snapshot(session: aiohttp.ClientSession, url: str, folder: str, prefix: str = "",
                              page: Optional[int] = None, timeout: int = DEFAULT_ASYNC_TIMEOUT,
                              max_size: int = MAX_HTML_SIZE) -> Optional[str]:
    """
    Asynchronous snapshot saver using aiohttp. Returns filepath or None.
    Truncates HTML if it exceeds max_size.
    """
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra = f"_p{page}" if page else ""
    slug = safe_filename(url)
    filename = f"{prefix}_{today}{extra}_{slug}.html"
    filepath = os.path.join(folder, filename)

    try:
        # aiohttp timeout wrapper
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with session.get(url, timeout=timeout_obj) as resp:
            resp.raise_for_status()
            text = await resp.text()
            if max_size and len(text) > max_size:
                text = text[:max_size]
        # write to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath
    except Exception as e:
        print(f"⚠️ Async download failed: {url}: {e}")
        return None


async def download_with_retry(session: aiohttp.ClientSession, url: str, folder: str, prefix: str,
                              retries: int = 3, backoff: tuple = (1.0, 3.0),
                              page: Optional[int] = None) -> Optional[str]:
    """
    Retry wrapper for async_save_snapshot.
    `backoff` is (min, max) seconds to wait randomly between retries.
    """
    for attempt in range(1, retries + 1):
        snap = await async_save_snapshot(session, url, folder, prefix, page=page)
        if snap:
            return snap
        if attempt < retries:
            wait = random.uniform(backoff[0], backoff[1])
            await asyncio.sleep(wait)
            print(f"⚠️ Retry {attempt}/{retries} for {url} (waited {wait:.1f}s)")
    print(f"❌ Giving up on {url} after {retries} attempts.")
    return None


# Image downloaders
def download_image(image_url: str, product_url: str, folder: str,
                   collection=None, db_filter: dict | None = None,
                   seen_hashes: Optional[Set[str]] = None,
                   timeout: int = 20) -> Optional[str]:
    """
    Synchronous image downloader using requests.
    Avoids duplicates using seen_hashes (pass a set to persist across calls).
    If `collection` and `db_filter` are provided, will return DB image_path if found.
    """
    if not image_url:
        return None
    if seen_hashes is None:
        seen_hashes = set()

    os.makedirs(folder, exist_ok=True)
    slug = safe_filename(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if os.path.exists(filepath):
        return filepath

    try:
        resp = requests.get(image_url, headers={"User-Agent": UserAgent().random if UserAgent else DEFAULT_USER_AGENT},
                            timeout=timeout)
        resp.raise_for_status()
        img_bytes = resp.content
        img_hash = content_hash(img_bytes)
        if img_hash in seen_hashes:
            # file already recorded; but return the path we would use
            return filepath
        seen_hashes.add(img_hash)

        # check DB for existing path if requested
        if collection is not None and db_filter:
            existing = collection.find_one(db_filter)
            if existing and existing.get("image_path"):
                return existing["image_path"]

        with open(filepath, "wb") as f:
            f.write(img_bytes)
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to download image {image_url}: {e}")
        return None


async def async_download_image(session: aiohttp.ClientSession, image_url: str, product_url: str,
                               folder: str, collection=None, db_filter: dict | None = None,
                               seen_hashes: Optional[Set[str]] = None,
                               timeout: int = DEFAULT_ASYNC_TIMEOUT) -> Optional[str]:
    """
    Async image downloader using aiohttp.
    """
    if not image_url:
        return None
    if seen_hashes is None:
        seen_hashes = set()

    os.makedirs(folder, exist_ok=True)
    slug = safe_filename(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if os.path.exists(filepath):
        return filepath

    try:
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        async with session.get(image_url, timeout=timeout_obj) as resp:
            resp.raise_for_status()
            img_bytes = await resp.read()

        img_hash = content_hash(img_bytes)
        if img_hash in seen_hashes:
            return filepath
        seen_hashes.add(img_hash)

        if collection is not None and db_filter:
            existing = collection.find_one(db_filter)
            if existing and existing.get("image_path"):
                return existing["image_path"]

        # write file in async-friendly thread
        await asyncio.to_thread(_write_binary_file, filepath, img_bytes)
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to async download image {image_url}: {e}")
        return None


def _write_binary_file(path: str, data: bytes) -> None:
    """Helper to write binary data to disk (used with asyncio.to_thread)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# Mongo helpers

def upsert_product(data, db_or_conn, db_name=None, collection_name=None, unique_keys=("url",), verbose=False):
    """
    Flexible upsert that accepts either a MongoClient instance or connection string.
    """
    if isinstance(db_or_conn, MongoClient):
        db = db_or_conn[db_name]
    else:
        db = MongoClient(db_or_conn)[db_name]

    if not collection_name:
        raise ValueError("collection_name is required")

    collection = db[collection_name]
    query = {k: data[k] for k in unique_keys if k in data}
    if not query:
        raise ValueError(f"None of {unique_keys} found in data")

    result = collection.update_one(query, {"$set": data}, upsert=True)
    if verbose:
        print(("🔁 Updated" if result.matched_count else "🆕 Inserted"), data.get("name", "<unknown>"))
    return "updated" if result.matched_count else "inserted"



# Cleanup helpers



DEBUG = True  # ensure this matches your global debug flag

async def async_remove_non_internal_storage(conn_string: str, db_name: str, image_dir: str = "product_images") -> None:
    """
    Asynchronously removes non-internal storage drives and their images from the MongoDB 'Storage' collection.
    Uses asyncio.to_thread() to offload blocking I/O for responsiveness.
    """
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db["Storage"]

    print("\n🔍 Starting async cleanup for non-internal storage drives...")
    removed = 0

    # Fetch items in a thread to avoid blocking the event loop
    items = await asyncio.to_thread(
        lambda: list(collection.find({}, {"specifications": 1, "name": 1, "url": 1, "image_path": 1}))
    )

    async def check_and_remove(item):
        nonlocal removed
        try:
            specs = item.get("specifications", {}) or {}
            specs_text = " ".join([f"{k} {v}".lower() for k, v in specs.items()])

            if "internal" not in specs_text:
                # Delete database entry
                await asyncio.to_thread(collection.delete_one, {"url": item["url"]})
                removed += 1
                print(f"🗑️ Removed non-internal storage: {item.get('name')}")

                # Remove image file if exists
                image_path = item.get("image_path")
                if image_path and os.path.exists(image_path):
                    try:
                        await asyncio.to_thread(os.remove, image_path)
                        if DEBUG:
                            print(f"🧹 Deleted image: {image_path}")
                    except Exception as e:
                        if DEBUG:
                            print(f"⚠️ Failed to delete image {image_path}: {e}")

        except Exception as e:
            if DEBUG:
                print(f"⚠️ Error processing {item.get('name', 'Unknown')}: {e}")

    # Run all checks concurrently
    tasks = [check_and_remove(item) for item in items]
    await asyncio.gather(*tasks)

    print(f"✅ Async cleanup complete — removed {removed} non-internal drives and their images.\n")



def input_with_timeout(prompt: str, timeout: int = 10) -> str:
    """Prompt user for input with timeout (auto default)."""
    print(f"{prompt} (auto-selects ALL after {timeout}s): ", end="", flush=True)
    q: queue.Queue = queue.Queue()

    def read_input():
        try:
            q.put(input())
        except Exception:
            q.put("")

    threading.Thread(target=read_input, daemon=True).start()
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        print("\nAuto-selecting ALL.")
        return ""


# HTML parsing helpers
def parse_product_page(html_file_path: str, product_url: Optional[str] = None,
                       image_url: Optional[str] = None, collection=None) -> Dict[str, Any]:
    """
    Parse product details from saved HTML.
    Returns a dict suitable for `upsert_product`.
    """
    # open file
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # --- Product name ---
    name_el = soup.select_one("h1.product-name-title")
    name = name_el.get_text(strip=True) if name_el else None

    # --- Prices ---
    price_new = soup.select_one("span.price-new")
    price_old = soup.select_one("span.price-old")
    discount_el = soup.select_one(".discount-percentage")

    prices = {
        "discounted": price_new.get_text(strip=True) if price_new else None,
        "original": price_old.get_text(strip=True) if price_old else None,
        "discount": discount_el.get_text(strip=True) if discount_el else None,
    }

    # --- Stock status ---
    stock_el = soup.select_one("span.base-color.ms-auto")
    stock_status = stock_el.get_text(strip=True) if stock_el else None

    # --- Specifications ---
    specifications: Dict[str, str] = {}
    for row in soup.select("div#tab-specification table.table tr"):
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            specifications[key] = value

    # --- Image download (synchronous) ---
    local_image_path = None
    try:
        images_folder = os.path.join(os.path.dirname(html_file_path), "images")
        local_image_path = download_image(
            image_url,
            product_url=product_url,
            folder=images_folder,
            collection=collection,
            db_filter={"url": product_url}
        )
    except Exception:
        local_image_path = None

    product_data = {
        "name": name,
        "url": product_url,
        "image_path": local_image_path,
        "price": prices,
        "stock_status": stock_status,
        "specifications": specifications,
        "source": "MD Computers",
        # store scraped_at as ISO if desired, but prefer datetime objects in DB so store datetime here:
        "scraped_at": datetime.now(timezone.utc),
    }

    return product_data

import os
import asyncio
import aiohttp
from pymongo import MongoClient
from fake_useragent import UserAgent
from urllib.parse import urlparse
from bson import ObjectId

DEBUG = True  # match your global debug flag


async def async_recover_missing_images(conn_string: str, db_name: str, image_dir: str = "product_images", concurrency: int = 15):
    """
    Asynchronously scans all MongoDB collections for missing image files.
    If an image file is missing, it redownloads the image and updates the MongoDB document.
    """

    client = MongoClient(conn_string)
    db = client[db_name]
    ua = UserAgent()

    print("\n🔍 Starting async image recovery check...")
    collections = db.list_collection_names()

    semaphore = asyncio.Semaphore(concurrency)
    total_missing = 0
    total_fixed = 0

    async with aiohttp.ClientSession() as session:

        async def check_and_fix_image(collection_name, doc):
            nonlocal total_missing, total_fixed
            async with semaphore:
                try:
                    image_url = doc.get("image_url")
                    image_path = doc.get("image_path")
                    name = doc.get("name", "Unknown")
                    url = doc.get("url")

                    # Validate: does image_path exist?
                    if not image_path or not os.path.exists(image_path):
                        total_missing += 1

                        if not image_url:
                            if DEBUG:
                                print(f"⚠️ Missing image URL for {name}")
                            return

                        # Build new image filename
                        parsed = urlparse(url)
                        safe_name = parsed.path.replace("/", "_").strip("_")
                        ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
                        new_filename = f"{safe_name}{ext}"
                        new_path = os.path.join(image_dir, new_filename)

                        os.makedirs(image_dir, exist_ok=True)

                        # Download asynchronously
                        headers = {"User-Agent": ua.random}
                        try:
                            async with session.get(image_url, headers=headers, timeout=20) as resp:
                                resp.raise_for_status()
                                content = await resp.read()
                            await asyncio.to_thread(open(new_path, "wb").write, content)

                            # Update DB document
                            await asyncio.to_thread(
                                db[collection_name].update_one,
                                {"_id": doc["_id"]},
                                {"$set": {"image_path": new_path}}
                            )
                            total_fixed += 1

                            if DEBUG:
                                print(f"🧩 Recovered image for {name} → {new_path}")

                        except Exception as e:
                            if DEBUG:
                                print(f"❌ Failed to redownload {name}: {e}")

                except Exception as e:
                    if DEBUG:
                        print(f"⚠️ Error processing doc in {collection_name}: {e}")

        # --- Traverse all collections concurrently ---
        for collection_name in collections:
            collection = db[collection_name]
            docs = await asyncio.to_thread(
                lambda: list(collection.find({}, {"_id": 1, "url": 1, "image_url": 1, "image_path": 1, "name": 1}))
            )

            print(f"\n📂 Checking collection: {collection_name} ({len(docs)} docs)")
            tasks = [check_and_fix_image(collection_name, doc) for doc in docs]
            await asyncio.gather(*tasks)

        print(f"\n✅ Image recovery complete.")
        print(f"Missing images found: {total_missing}")
        print(f"Recovered successfully: {total_fixed}\n")
