# --- common_functions.py ---
import os
import json
import requests
import hashlib
import threading
import queue
import random
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# ----------------------------
#  🧠 Utility Functions
# ----------------------------
def slugify(url: str) -> str:
    """Convert URL to a filesystem-safe string."""
    return (
        url.replace("https://", "")
        .replace("http://", "")
        .replace("/", "_")
        .replace("?", "_")
        .replace("&", "_")
        .replace("=", "_")
    )


def content_hash(content):
    """Create an MD5 hash for deduplication."""
    h = hashlib.md5()
    if isinstance(content, str):
        content = content.encode("utf-8")
    h.update(content)
    return h.hexdigest()


def save_json(data, folder, prefix="data"):
    """
    Save scraped data to a timestamped JSON file.
    Also deletes old JSONs (>2 days).
    """
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).date()

    # Cleanup old files
    for filename in os.listdir(folder):
        if filename.endswith(".json") and filename.startswith(prefix):
            try:
                date_str = filename.rsplit("_", 1)[-1].replace(".json", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if (today - file_date).days > 2:
                    print(f"🗑️ Deleting old file: {filename}")
                    os.remove(os.path.join(folder, filename))
            except Exception:
                pass

    # Save new file
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = os.path.join(folder, f"{prefix}_{timestamp}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def save_snapshot(url, folder, prefix="", page=None):
    """Download and save HTML snapshot for later parsing."""
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra = f"_p{page}" if page else ""
    slug = slugify(url)
    filename = f"{prefix}_{today}{extra}_{slug}.html"
    filepath = os.path.join(folder, filename)

    try:
        response = requests.get(url, headers={"User-Agent": UserAgent().random})
        response.raise_for_status()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(response.text)
        return filepath
    except Exception as e:
        print(f"⚠️ Failed to save snapshot for {url}: {e}")
        return None


def download_image(image_url, product_url, folder, collection=None, db_filter=None, seen_hashes=set()):
    """Downloads and stores an image locally (with duplicate protection)."""
    if not image_url:
        return None

    os.makedirs(folder, exist_ok=True)
    slug = slugify(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if os.path.exists(filepath):
        return filepath

    try:
        response = requests.get(image_url, headers={"User-Agent": UserAgent().random})
        response.raise_for_status()
        img_bytes = response.content
        img_hash = content_hash(img_bytes)

        # Avoid duplicates
        if img_hash in seen_hashes:
            return filepath
        seen_hashes.add(img_hash)

        # Check if already in DB
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


def upsert_product(data, conn_string, db_name, collection_name, unique_keys=("url",), verbose=False):
    """
    Inserts or updates a product in MongoDB based on unique keys.
    Always overwrites existing data. Avoids duplicate inserts.
    """
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db[collection_name]

    # Build unique query
    query = {k: data[k] for k in unique_keys if k in data}
    if not query:
        raise ValueError(f"None of {unique_keys} found in data")

    result = collection.update_one(query, {"$set": data}, upsert=True)
    if verbose:
        if result.matched_count > 0:
            print(f"🔁 Updated: {data.get('name', 'Unknown product')}")
        else:
            print(f"🆕 Inserted: {data.get('name', 'Unknown product')}")
    return "updated" if result.matched_count > 0 else "inserted"


def remove_non_internal_storage(conn_string, db_name):
    """Removes non-internal storage drives from the database."""
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db["Storage"]

    removed = 0
    for item in collection.find({}, {"specifications": 1, "name": 1, "url": 1}):
        specs_text = " ".join([f"{k} {v}".lower() for k, v in item.get("specifications", {}).items()])
        if "internal" not in specs_text:
            collection.delete_one({"url": item["url"]})
            removed += 1
            print(f"🗑️ Removed non-internal storage: {item.get('name')}")

    print(f"✅ Cleanup complete — removed {removed} non-internal drives.")

def input_with_timeout(prompt, timeout=10):
    """Prompt user for input with timeout (auto default)."""
    print(f"{prompt} (auto-selects ALL after {timeout}s): ", end="", flush=True)
    q = queue.Queue()

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


def parse_product_page(html_file_path, product_url=None, image_url=None, collection=None):
    """Parse product details from saved HTML."""
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
    specifications = {}
    for row in soup.select("div#tab-specification table.table tr"):
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            specifications[key] = value

    # --- Image download ---
    local_image_path = download_image(
        image_url,
        product_url=product_url,
        folder=os.path.join(os.path.dirname(html_file_path), "images"),
        collection=collection,
        db_filter={"url": product_url}
    )

    product_data = {
        "name": name,
        "url": product_url,
        "image_path": local_image_path,
        "price": prices,
        "stock_status": stock_status,
        "specifications": specifications,
        "source": "MD Computers",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    return product_data
