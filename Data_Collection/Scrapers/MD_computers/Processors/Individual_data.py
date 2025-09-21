import os
import json
import glob
import datetime
from bs4 import BeautifulSoup
import Data_Collection.Scrapers.MD_computers.Processors.common_functions as cf
import time
from pymongo import MongoClient

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


def parse_product_page(html_file_path, product_url=None, image_url=None, collection=None):
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
    local_image_path = cf.download_image(
        image_url,
        product_url=product_url,
        folder=IMAGE_DIR,
        collection=collection,
        db_filter={"url": product_url}  # Find the product by URL
    )

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



if __name__ == "__main__":

    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    json_files = glob.glob(os.path.join(JSON_FILE_PATH, "processors_*.json"))
    if not json_files:
        raise FileNotFoundError("No JSON files found in Raw_data directory.")

    #-- Ask the user to select which file --
    print("\nAvailable JSON files:")
    for i, f in enumerate(sorted(json_files), 1):
        print(f"{i}. {os.path.basename(f)}")

    choice = input("\nEnter the number of the file to use (press Enter to use latest): ").strip()

    if choice and choice.isdigit() and 1 <= int(choice) <= len(json_files):
        raw_data_file = sorted(json_files)[int(choice) - 1]
    else:
        raw_data_file = max(json_files, key=os.path.getmtime)  # Default to latest

    print(f"\nUsing file: {os.path.basename(raw_data_file)}\n")

    with open(raw_data_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    for item in products:
        url = item.get("url")
        image_url = item.get("image_url")
        if not url:
            continue

        # Save snapshot
        html_file = cf.save_snapshot(url, SNAPSHOT_DIR, prefix="mdcomputers")

        # Parse product
        product_data = parse_product_page(html_file, product_url=url, image_url=image_url, collection=collection)

        # Save to Mongo
        cf.upsert_product(product_data, CONNECTION_STRING, DB_NAME, COLLECTION_NAME)

        print(f"Successfully saved {product_data['name']}.")

        # Delete HTML snapshot after saving to DB
        try:
            os.remove(html_file)
            print(f"Deleted snapshot: {html_file}\n")
        except Exception as e:
            print(f"Failed to delete snapshot {html_file}: {e}\n")

    # Cleanup obsolete images
    for img_file in os.listdir(IMAGE_DIR):
        img_path = os.path.join(IMAGE_DIR, img_file)
        if not collection.find_one({"image_path": img_path}):
            os.remove(img_path)
            print(f"Deleted obsolete image: {img_path}")

''' --- bakchodi nhi mittar --- g phad dunga kuch hua to ---'''