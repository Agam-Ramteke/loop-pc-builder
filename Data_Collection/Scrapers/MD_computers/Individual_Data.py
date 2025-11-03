import json
import glob
import datetime
from bs4 import BeautifulSoup
from unicodedata import category
import threading
import queue
import sys
import time
import random
import urllib.request
import traceback
import os
import asyncio

import common_functions as cf
from pymongo import MongoClient

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "individual_snapshots")
IMAGE_DIR = os.path.join(BASE_DIR, "product_images")
DATA_DIR = os.path.join(BASE_DIR, "DATA_DIR")


os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

# MongoDB settings
DB_NAME = "PC_Parts"
COLLECTION_NAME = None
CONNECTION_STRING = "mongodb://localhost:27017/"



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
        "scraped_at": datetime.datetime.utcnow().isoformat()
    }

    return product_data


def input_with_timeout(prompt, timeout=10):
    """
    Waits for user input for a limited time.
    Returns input string if entered within timeout, else returns ''.
    Works safely even in PyCharm or VSCode.
    """
    print(f"{prompt} (auto-selects ALL after {timeout} seconds): ", end="", flush=True)
    q = queue.Queue()

    def read_input():
        try:
            user_input = input()
            q.put(user_input)
        except Exception:
            q.put("")  # fallback for IDE consoles that block input()

    t = threading.Thread(target=read_input, daemon=True)
    t.start()

    try:
        user_input = q.get(timeout=timeout)
        return user_input
    except queue.Empty:
        print("\n⏰ Timeout reached. Automatically selecting ALL categories.")
        return ""

if __name__ == "__main__":

    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    # --- Load all JSON files ---
    all_json_files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    if not all_json_files:
        raise FileNotFoundError(f"No JSON files found in {DATA_DIR} directory.")

    print(f"Available Component files: ")
    for i, file in enumerate(sorted(all_json_files),1):
        print(f"{i}.{os.path.basename(file)}")

    #---Allow user to select one or all at once---
    choice = input_with_timeout("\n Enter the number of files to process", timeout=10).strip()

    files_to_process = []
    if choice and choice.isdigit() and 1 <= int(choice) <= len(all_json_files):
        files_to_process = [sorted(all_json_files)[int(choice)-1]]
    else:
        files_to_process = all_json_files # sab process karlo

    for raw_data_file in files_to_process:
        file_name = os.path.basename(raw_data_file)
        print(f"Processing File : {file_name}")

        #Extract Component Details ( Dynamically )
        base_name = file_name.split("_")[0].lower()
        mapping = {
            "graphics-card": "GPUs",
            "processor": "Processors",
            "ram": "RAM",
            "motherboard": "Motherboards",
            "smps": "smps",
            "storage": "Storage",
            "cabinet": "Cabinets"
        }

        collection_name = mapping.get(base_name, base_name.capitalize())
        collection = db[collection_name]

        print(f"Target MongoDB collection : {collection_name}")

        with open(raw_data_file,"r",encoding="utf-8") as f:
            products = json.load(f)


        #---Process Each element---
        for item in products:
            url = item["url"]
            image_url = item.get("image_url")
            scraped_at = item.get("Scraped_at")
            if not url:
                continue

            # Save Snapshot
            html_file = cf.save_snapshot(url,SNAPSHOT_DIR,prefix="mdcomputers")

            #Parse And Save
            product_data = parse_product_page(html_file,product_url = url, image_url = image_url,collection = collection)

            if collection_name.lower() == "storage":
                specs_text = " ".join([f"{k} {v}".lower() for k, v in product_data.get("specifications", {}).items()])
                if "internal" not in specs_text:
                    print(f"Skipping Non-Internal Storage : {product_data['name']}")
                    continue

            result = cf.upsert_product(product_data, CONNECTION_STRING, DB_NAME, collection_name)

            # Only delete snapshot if we actually processed it (inserted or updated)
            if result == "inserted":
                print(f"Saved: {product_data['name']}")
                time.sleep(random.uniform(2, 3))

                try:
                    os.remove(html_file)
                    print(f"Deleted snapshot: {html_file}\n")
                except Exception as e:
                    print(f"Failed to delete snapshot {html_file}: {e}\n")
            elif result == "skipped":
                # Delete snapshot immediately since we didn't process it
                try:
                    os.remove(html_file)
                    print(f"Deleted snapshot: {html_file}\n")
                except Exception as e:
                    print(f"Failed to delete snapshot {html_file}: {e}\n")


            print(f"Saved : {product_data['name']}")
            time.sleep(random.uniform(2,3))


            # Cleanup snapshot only if not skipped
            try:
                os.remove(html_file)
                print(f"Deleted snapshot: {html_file}\n")
            except Exception as e:
                print(f"Failed to delete snapshot {html_file}: {e}\n")

            # --- Cleanup obsolete images for this category ---
        for img_file in os.listdir(IMAGE_DIR):
            img_path = os.path.join(IMAGE_DIR, img_file)
            if not collection.find_one({"image_path": img_path}):
                os.remove(img_path)
                print(f"Deleted obsolete image: {img_path}")

        print("\n🎉 All selected component data processed successfully!")