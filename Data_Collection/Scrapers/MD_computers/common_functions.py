#Importing Modules
import os
import requests
from fake_useragent import UserAgent
import json
from pymongo import MongoClient
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import aiohttp
import asyncio
from datetime import timezone

def slugify(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_")


def save_json(data, folder, prefix="data"):
    #--Cleanup Files older than 2 weeks(14 days)--
    today = datetime.now(timezone.utc).date()
    for filename in os.listdir(folder):
        if filename.endswith(".json") and filename.startswith(prefix):
            try:
                date_str = filename.rsplit("_", 1)[-1].replace(".json", "")
                file_date = datetime.strptime(date_str,"%Y-%m-%d").date()
                if (today - file_date).days > 2: #change this every run Q_Q . cause idk me kyu ye likh testing ke phase me
                    print(f"Deleting Older File : : {filename}")
                    os.remove(os.path.join(folder, filename))
            except Exception as e:
                print(f"Error processing file {filename}: {e}")


    #--Save new file--    
    
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filepath = os.path.join(folder, f"{prefix}_{today}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


    return filepath

def save_to_mongo(data, conn_string, db_name, collection_name):
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db[collection_name]
    collection.insert_one(data)

def content_hash(content):
    h = hashlib.md5()
    if isinstance(content, str):
        content = content.encode('utf-8')
    h.update(content)
    return h.hexdigest()

def download_image(image_url, product_url, folder, collection=None, db_filter=None, seen_hashes=set()):
    if seen_hashes is None:
        seen_hashes = set()
    os.makedirs(folder, exist_ok=True)
    slug = slugify(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if not os.path.exists(filepath):
        try:
            response = requests.get(image_url, headers={"User-Agent": UserAgent().random})
            response.raise_for_status()
            img_bytes = response.content
            h = content_hash(img_bytes)

            if h in seen_hashes:
                print(f"Duplicate detected: {image_url}")
                return seen_hashes[h]
            else:
                # Check in DB before saving
                if collection is not None and db_filter:
                    existing = collection.find_one(db_filter)
                    if existing and existing.get("image_path"):
                        # Image already exists in DB
                        return existing["image_path"]

                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                seen_hashes.add(h)
        except Exception:
            return None
    return filepath

def save_snapshot(url, folder, prefix="", page=None):
    """Generic snapshot saver"""
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra = f"_p{page}" if page else ""
    slug = slugify(url)
    filename = f"{prefix}_{today}{extra}_{slug}.html"
    filepath = os.path.join(folder, filename)

    response = requests.get(url, headers={"User-Agent": UserAgent().random})
    response.raise_for_status()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)

    return filepath


def upsert_product(data, conn_string, db_name, collection_name, unique_keys=("url",), verbose=True):
    """
    Inserts or updates a product in MongoDB based on unique keys.
    Updates only if the existing record is older than 2 days.

    Returns:
        "inserted" - new document created
        "updated" - existing document updated
        "skipped" - document exists and is fresh (< 2 days old)
    """
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db[collection_name]

    # --- Build query using unique keys ---
    query = {k: data[k] for k in unique_keys if k in data}
    if not query:
        raise ValueError(f"None of the unique keys {unique_keys} found in data")

    # --- Check for existing record ---
    existing = collection.find_one(query)

    if existing:
        scraped_at_str = existing.get("scraped_at")
        if scraped_at_str:
            try:
                scraped_at = datetime.fromisoformat(scraped_at_str)
                age = datetime.now(timezone.utc) - scraped_at

                # Skip if not older than 2 days
                if age < timedelta(days=2):
                    if age.days == 0:
                        hours = age.seconds // 3600
                        mins = (age.seconds % 3600) // 60
                        time_str = f"{hours}h {mins}m ago" if hours else f"{mins}m ago"
                    else:
                        time_str = f"{age.days} day{'s' if age.days > 1 else ''} ago"

                    if verbose:
                        print(f"Skipped (fresh data {time_str}): {data.get('name', 'Unknown product')}")
                    return "skipped"

            except Exception as e:
                print(f"Failed to parse scraped_at for {data.get('name')}: {e}")

        # --- Update existing record ---
        collection.update_one(query, {"$set": data}, upsert=True)
        if verbose:
            print(f"Updated: {data.get('name', 'Unknown product')}")
        return "updated"

    else:
        # --- Insert new record ---
        collection.insert_one(data)
        if verbose:
            print(f"Inserted new: {data.get('name', 'Unknown product')}")
        return "inserted"




def delete_non_internal():
    from pymongo import MongoClient

    client = MongoClient("localhost:27017")
    db = client["PC_Parts"]
    collection = db["Storage"]

    result = collection.delete_many({
        "specifications.Category": {"$not": {"$regex": "internal", "$options": "i"}}
    })

    print(f"Deleted {result.deleted_count} non-internal SSD entries.")

def next_page(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
    next_link = soup.find("link", rel="next")
    return bool(next_link)