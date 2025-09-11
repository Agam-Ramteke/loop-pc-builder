import os
import requests
from bs4 import BeautifulSoup
import datetime
import json
from fake_useragent import UserAgent

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
DATA_DIR = os.path.join(BASE_DIR, "Raw_data")

URL = "https://mdcomputers.in/catalog/processor"

# Ensure directories exist
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def save_snapshot(page=1):
    """Download and save the HTML snapshot for a given page."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = f"mdcomputers_{today}_p{page}.html"
    filepath = os.path.join(SNAPSHOT_DIR, filename)

    url = URL if page == 1 else f"{URL}?page={page}"
    response = requests.get(url, headers={"User-Agent": UserAgent().random})
    response.raise_for_status()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"Snapshot saved: {filepath}")
    return filepath


def parse_snapshot(filepath):
    """Scrape processor data from saved HTML snapshot."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    processors = []

    # Product blocks
    product_blocks = soup.select("div.product-grid-item")
    if not product_blocks:
        return []

    for product in product_blocks:
        # Title & URL
        name_el = product.select_one("h3.product-entities-title a")
        name = name_el.get_text(strip=True) if name_el else None
        url = name_el["href"].strip() if name_el and name_el.has_attr("href") else None

        # Image (handle both src and lazy attributes)
        img_el = product.select_one("img")
        image_url = None
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src")

        # Prices
        price_del = product.select_one("span.price span.del")
        price_ins = product.select_one("span.price span.ins")
        original_price = price_del.get_text(strip=True) if price_del else None
        discounted_price = price_ins.get_text(strip=True) if price_ins else None

        # Discount badge
        discount_el = product.select_one(".onsale") or product.select_one(".product-labels .onsale")
        discount = discount_el.get_text(strip=True) if discount_el else None

        processors.append({
            "name": name,
            "url": url,
            "image_url": image_url,
            "original_price": original_price,
            "discounted_price": discounted_price,
            "discount": discount
        })

    return processors


def save_data(data):
    """Save scraped data as JSON with timestamp."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    filepath = os.path.join(DATA_DIR, f"processors_{today}.json")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Data saved: {filepath}")


if __name__ == "__main__":
    all_processors = []
    page = 1

    while True:
        html_file = save_snapshot(page)
        processors = parse_snapshot(html_file)

        if not processors:
            print(f"❌ No products on page {page}, stopping.")
            break

        print(f"✅ Page {page}: Found {len(processors)} products")
        all_processors.extend(processors)
        page += 1

    save_data(all_processors)
