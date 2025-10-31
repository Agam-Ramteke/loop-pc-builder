import time
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import os
import json
import common_functions as cf
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

# Settings
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
DATA_DIR = os.path.join(BASE_DIR, "DATA_DIR")


URL = [
    "https://mdcomputers.in/catalog/processor",
    "https://mdcomputers.in/catalog/graphics-card",
    "https://mdcomputers.in/catalog/ram",
    "https://mdcomputers.in/catalog/storage",
    "https://mdcomputers.in/catalog/smps",
    "https://mdcomputers.in/catalog/cabinet"]

# Ensure directories exist
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

def parse_snapshot(filepath):
    with open(filepath, "rb") as f:
        soup = BeautifulSoup(f, "html.parser")

    items = []
    product_blocks = soup.select("div.product-grid-item")
    if not product_blocks:
        return []
    
    for product in product_blocks:
        # --- Name and URL ---
        name_el = product.select_one("h3.product-entities-title a")
        name = name_el.get_text(strip=True) if name_el else None
        url = name_el["href"].strip() if name_el and name_el.has_attr("href") else None

        # --- Image ---
        image_el = product.select_one("img")
        image_url = None
        if image_el:
            image_url = (
                image_el.get("src")
                or image_el.get("data-src")
                or image_el.get("data-lazy-src")
                or image_el.get("data-cfsrc")  # Cloudflare Lazy Loading
            )
            # Fallback: check <noscript><img src="..."></noscript>
            if not image_url:
                noscript_img = product.select_one("noscript img")
                if noscript_img and noscript_img.get("src"):
                    image_url = noscript_img["src"]

            # Add domain if it's a relative path
            if image_url and image_url.startswith("/"):
                image_url = "https://mdcomputers.in" + image_url

        # --- Prices ---
        price_del = product.select_one("span.price span.del")
        price_ins = product.select_one("span.price span.ins")
        original_price = price_del.get_text(strip=True) if price_del else None
        discounted_price = price_ins.get_text(strip=True) if price_ins else None

        #-- Append item data --
        items.append({
            "name": name,
            "url": url,
            "image_url": image_url,
            "price": {
                "original": original_price,
                "discounted": discounted_price,
                "discount": None
            },
            "stock_status": None,
            "specifications": {},  # Leave empty for now
            "source": "MD Computers"
        })

    return items

if __name__ == "__main__":
    for link in URL:
        path = urlparse(link).path
        item_name = Path(path).name
        print("\n" + "=" * 60 + "\n")
        print(f"Processing snapshots for: {item_name.upper()}")

        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"{item_name}_{today}.json"
        filepath = os.path.join(DATA_DIR, filename)
        if os.path.exists(filepath):
            print(f"✔ Entry for {item_name} already exists — skipping scrape.\n")
            continue

        all_items = []
        page = 1

        while True:
            page_url = link  if page == 1 else f"{link}?page={page}"
            html_file = cf.save_snapshot(page_url,SNAPSHOT_DIR,"MD Computers",page = page)
            all_items = parse_snapshot(html_file)
            has_next = cf.next_page(html_file)

            try:
                os.remove(html_file)
                print(f"Processed snapshot for {item_name} page {page}")
            except Exception as e:
                print(f"Failed to delete snapshot for {item_name} page {page}: {e}")

            if not all_items:
                print(f"No  Products on page {page}")

            if not has_next:
                print(f"No more pages found after page {page}\n")
                break
            page += 1
            time.sleep(0.15)
        cf.save_json(all_items, DATA_DIR,prefix= item_name)

