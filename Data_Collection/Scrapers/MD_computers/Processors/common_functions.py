import os
import datetime
import requests
from fake_useragent import UserAgent
import json
from pymongo import MongoClient

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

def download_image(image_url, product_url, folder):
    os.makedirs(folder, exist_ok=True)
    slug = slugify(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if not os.path.exists(filepath):
        try:
            response = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
        except Exception:
            return None
    return filepath

def save_json(data, folder, prefix="data"):
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
