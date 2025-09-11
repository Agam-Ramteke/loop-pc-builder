from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup
import datetime
import os
import json
import re
from pymongo import MongoClient 
import glob

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "individual_snapshots")
IMAGE_DIR = os.path.join(BASE_DIR, "product_images")
JSON_FILE_PATH = os.path.join(BASE_DIR, "Raw_data")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# MongoDB settings
DB_NAME = "PC_Parts"
COLLECTION_NAME = "Processors"
CONNECTION_STRING = "localhost:27017"


def slugify(url):
    """Make a filesystem-safe filename fragment from product URL."""
    return re.sub(r"[^a-zA-Z0-9]+", "_", url.strip().rstrip("/"))


def save_snapshot(url):
    """Download and save the HTML snapshot for a given product page."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    slug = slugify(url)
    filename = f"mdcomputers_{today}_{slug}.html"
    filepath = os.path.join(SNAPSHOT_DIR, filename)

    response = requests.get(url, headers={"User-Agent": UserAgent().random})
    response.raise_for_status()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"Snapshot saved: {filepath}")
    return filepath


def download_image(image_url, product_url):
    """Download an image from URL with a unique filename based on the product URL."""
    if not image_url:
        return None

    # Use slugified product URL to make the image filename unique
    url_slug = slugify(product_url)
    ext = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filename = f"{url_slug}{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)

    if not os.path.exists(filepath):
        try:
            response = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            print(f"Image downloaded: {filename}")
        except Exception as e:
            print(f"Failed to download image {image_url}: {e}")
            return None

    return filepath



def parse_product_page(html_file_path, product_url=None, image_url=None):
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # --- Product Name ---
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

    # --- Stock Status ---
    stock_el = soup.select_one("span.base-color.ms-auto")
    stock_status = stock_el.get_text(strip=True) if stock_el else None

    # --- Specifications Table ---
    specifications = {}
    spec_rows = soup.select("div#tab-specification table.table tr")
    for row in spec_rows:
        cols = row.find_all("td")
        if len(cols) == 2:
            key = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            specifications[key] = value

    # --- Download image ---
    local_image_path = download_image(image_url, product_url) if image_url else None

    product_data = {
        "name": name,
        "url": product_url,
        "image_path": local_image_path,
        "price": prices,
        "stock_status": stock_status,
        "specifications": specifications,
        "source": "MD Computers",
        "scraped_at": datetime.datetime.utcnow().isoformat()
    }

    return product_data


def save_to_mongo(product_data):
    client = MongoClient(f"mongodb://{CONNECTION_STRING}")
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]
    
    result = collection.update_one(
        {"url": product_data["url"]},  # filter by URL
        {"$set": product_data},        # update with new data
        upsert=True
    )
    
    if result.upserted_id:
        print(f"Inserted new: {product_data['name']} with _id {result.upserted_id}")
    else:
        print(f"Updated existing: {product_data['name']}")


if __name__ == "__main__":
    
    json_files = glob.glob(os.path.join(JSON_FILE_PATH, "processors_*.json"))
    
    if not json_files:
        raise FileNotFoundError("No JSON files found in Raw_data directory.")
    
    raw_data_file = max(json_files, key=os.path.getmtime)
    with open(raw_data_file, "r", encoding="utf-8") as f:
        products = json.load(f)
    
    for item in products:
        url = item.get("url")
        image_url = item.get("image_url")
        if not url:
            continue
        
        html_file = save_snapshot(url)
        product_data = parse_product_page(html_file, product_url=url, image_url=image_url)
        save_to_mongo(product_data)

        # Delete HTML snapshot after saving to DB
        try:
            os.remove(html_file)
            print(f"Deleted snapshot: {html_file}")
        except Exception as e:
            print(f"Failed to delete snapshot {html_file}: {e}")

#--- Bakchodi ni mittar --- g phad dunga agar isme kuch gadbad hui to ---