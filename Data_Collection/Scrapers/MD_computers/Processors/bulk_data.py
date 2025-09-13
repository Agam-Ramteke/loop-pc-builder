import os
from bs4 import BeautifulSoup
import sys
import os
import common_functions as cf
# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, "snapshots")
DATA_DIR = os.path.join(BASE_DIR, "Raw_data")


URL = "https://mdcomputers.in/catalog/processor"

# Ensure directories exist
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def parse_snapshot(filepath):
    """Scrape processor data from saved HTML snapshot."""
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    processors = []
    product_blocks = soup.select("div.product-grid-item")
    if not product_blocks:
        return []

    for product in product_blocks:
        # --- Name & URL ---
        name_el = product.select_one("h3.product-entities-title a")
        name = name_el.get_text(strip=True) if name_el else None
        url = name_el["href"].strip() if name_el and name_el.has_attr("href") else None

        # --- Image ---
        img_el = product.select_one("img")
        image_url = None
        if img_el:
            image_url = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src")
            if image_url and image_url.startswith("/"):
                image_url = "https://mdcomputers.in" + image_url

        # --- Prices ---
        price_del = product.select_one("span.price span.del")
        price_ins = product.select_one("span.price span.ins")
        original_price = price_del.get_text(strip=True) if price_del else None
        discounted_price = price_ins.get_text(strip=True) if price_ins else None

        discount_el = product.select_one(".onsale") or product.select_one(".product-labels .onsale")
        discount = discount_el.get_text(strip=True) if discount_el else None

        # --- Unified schema (matches individual_data.py) ---
        processors.append({
            "name": name,
            "url": url,
            "image_url": image_url,
            "price": {
                "original": original_price,
                "discounted": discounted_price,
                "discount": discount,
            },
            # leave empty here – individual_data.py fills these later
            "stock_status": None,
            "specifications": {},
            "source": "MD Computers"
        })

    return processors


if __name__ == "__main__":
    all_processors = []
    page = 1

    while True:
        page_url = URL if page == 1 else f"{URL}?page={page}"
        html_file = cf.save_snapshot(page_url, SNAPSHOT_DIR, prefix="mdcomputers", page=page)
        processors = parse_snapshot(html_file)

        if not processors:
            print(f"❌ No products on page {page}, stopping.")
            break

        print(f"✅ Page {page}: Found {len(processors)} products")
        all_processors.extend(processors)

        # Clean up snapshot right after parsing
        try:
            os.remove(html_file)
            print(f"🗑️ Deleted snapshot: {html_file}")
        except Exception as e:
            print(f"⚠️ Failed to delete snapshot {html_file}: {e}")

        page += 1

    # Save combined JSON (all processors from all pages)
    cf.save_json(all_processors, DATA_DIR, prefix="processors")
