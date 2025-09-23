#Importing Modules
import os
import datetime
import requests
from fake_useragent import UserAgent
import json
from pymongo import MongoClient
import hashlib


def slugify(url: str) -> str:
    return url.replace("https://", "").replace("http://", "").replace("/", "_").replace("?", "_").replace("&", "_")

def save_snapshot(url, folder, prefix="", page=None):
    """Generic snapshot saver"""
    os.makedirs(folder, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    extra = f"_p{page}" if page else ""
    slug = slugify(url)
    filename = f"{prefix}_{today}{extra}_{slug}.html"
    filepath = os.path.join(folder, filename)

    response = requests.get(url, headers={"User-Agent": UserAgent().random})
    response.raise_for_status()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)

    return filepath

def save_json(data, folder, prefix="data"):
    #--Cleanup Files older than 2 weeks(14 days)--
    today = datetime.datetime.now().date()
    for filename in os.listdir(folder):
        if filename.endswith(".json") and filename.startswith(prefix):
            try:
                date_str =filename[len(prefix)+1:-5]
                file_date = datetime.datetime.strptime(date_str,"%Y-%m-%d").date()
                if (today - file_date).days > 14:
                    os.remove(os.path.join(folder, filename))
            except Exception as e:
                print(f"Error processing file {filename}: {e}")


    #--Save new file--    
    
    os.makedirs(folder, exist_ok=True)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
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
    h.update(content)
    return h.hexdigest()

def download_image(image_url, product_url, folder, collection=None, db_filter=None, seen_hashes=set()):
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

def upsert_product(data, conn_string, db_name, collection_name, unique_keys=("url",)):
    """
    Inserts or updates a product in MongoDB based on unique keys.

    Parameters:
    - data: dict of product
    - unique_keys: tuple of field names used to identify duplicates (default: "url")
    """
    client = MongoClient(conn_string)
    db = client[db_name]
    collection = db[collection_name]

    # Build query based on the unique keys that exist in data
    query = {k: data[k] for k in unique_keys if k in data}
    if not query:
        raise ValueError(f"None of the unique keys {unique_keys} found in data")

    # Upsert: update if exists, insert if not
    collection.update_one(query, {"$set": data}, upsert=True)
