"""
Download multiple collection pages -> parse product links -> download each product page temporarily
Parse fields into JSON and save to Elite Hubs/data/.
Also:
 - delete temporary HTML snapshots after use
 - prune JSON files older than PRUNE_DAYS (default 7 days)
"""

import requests
import tempfile
import os
import time
import json
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import fnmatch
import re
from datetime import date, datetime
import sys
from rich.console import Console
from rich.table import Table
from rich import box

# CONFIG
# Define collections here: key is filename prefix, value is collection URL
COLLECTIONS = {
    "processors": "https://www.elitehubs.com/collections/processor",
    "motherboard": "https://www.elitehubs.com/collections/motherboard",
    "nvidia_gpus": "https://elitehubs.com/collections/nvidia-graphic-cards",
    "amd_gpus": "https://elitehubs.com/collections/amd-graphic-cards",
    "ram": "https://elitehubs.com/collections/ram",
    "storage": "https://elitehubs.com/collections/storage-ssd-hard-disk",
    "pc_cabinet": "https://elitehubs.com/collections/pc-cabinet",
    "pc_coolers": "https://elitehubs.com/collections/pc-coolers",
    "psu": "https://elitehubs.com/collections/power-supply-unit-psu"
}

BASE_URL = "https://www.elitehubs.com"

# Polite headers (fake_useragent fallback handled below)
try:
    from fake_useragent import UserAgent
    UA = UserAgent().random
except Exception:
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")

HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}
DELAY_MIN, DELAY_MAX = 0.6, 1.2  # polite random delay between requests
PRUNE_DAYS = 7  # delete json files older than this (days)
MAX_PAGES = 30  # max pagination pages to check for a collection

# ---- SCRAPING SUMMARY ----
SCRAPE_SUMMARY = {}

def ensure_dirs():
    base = os.path.abspath(os.path.dirname(__file__))  # Elite Hubs folder
    data_dir = os.path.join(base, "data")
    snaps_dir = os.path.join(base, "async_snapshots")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(snaps_dir, exist_ok=True)
    return data_dir, snaps_dir


def download_to_file(url, dest_path, timeout=20):
    print("Downloading:", url)
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(r.text)
    return dest_path


def download_temp(url, timeout=20):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=".html", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(r.text)
    return path


def parse_product_page_from_temp(temp_path, url):
    with open(temp_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "lxml")

    def meta(prop):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    raw_title = meta("og:title") or (soup.title.string.strip() if soup.title else None)
    if raw_title:
        cleaned_title = raw_title.replace("Buy", "").replace("buy", "")
        cleaned_title = cleaned_title.replace("| EliteHubs.com", "").replace("EliteHubs.com", "").strip()
        if not cleaned_title:
            cleaned_title = raw_title.strip()
    else:
        cleaned_title = None

    image = meta("og:image:secure_url") or meta("og:image")
    price_amount = meta("og:price:amount")
    currency = meta("og:price:currency")

    original_price = None
    discounted_price = None
    if price_amount:
        discounted_price = price_amount

    text = soup.get_text(" ", strip=True)
    stock_status = None
    txt_lower = text.lower()
    if "out of stock" in txt_lower or "sold out" in txt_lower:
        stock_status = "Out of Stock"
    elif "in stock" in txt_lower:
        stock_status = "In Stock"

    compare_candidates = soup.select("[class*='compare'], [class*='original'], [class*='was-price'], [class*='price--compare']")
    for el in compare_candidates:
        s = el.get_text(" ", strip=True)
        if s and any(ch.isdigit() for ch in s):
            original_price = s
            break

    if not original_price:
        prices = re.findall(r"₹\s?[0-9,]+(?:\.\d+)?", text)
        if prices:
            if len(prices) >= 2:
                original_price, discounted_price = prices[0], prices[1]
            else:
                if not discounted_price:
                    discounted_price = prices[0]
                if not original_price:
                    original_price = prices[0]

    if not original_price and discounted_price:
        original_price = discounted_price
    if not discounted_price and original_price:
        discounted_price = original_price

    def clean(x):
        return x.strip() if isinstance(x, str) and x.strip() else None

    obj = {
        "name": clean(cleaned_title),
        "url": url,
        "image_url": clean(image),
        "scraped_at": datetime.now().astimezone().isoformat(),
        "price": {
            "original": clean(original_price),
            "discounted": clean(discounted_price),
            "discount": None
        },
        "stock_status": stock_status,
        "specifications": {},
        "source": "EliteHubs"
    }
    return obj


def get_product_links_shopify_json(collection_url):
    links = []
    page = 1

    while True:
        json_url = f"{collection_url}/products.json?limit=250&page={page}"
        r = requests.get(json_url, headers=HEADERS, timeout=20)

        if r.status_code != 200:
            break

        data = r.json()
        products = data.get("products", [])

        if not products:
            break

        for product in products:
            links.append(f"{BASE_URL}/products/{product['handle']}")

        page += 1
        time.sleep(random.uniform(0.3, 0.6))

    return links

# filename-date based pruning (deletes files like '<prefix>_YYYY-MM-DD.json' older than days)
def prune_old_jsons(data_dir, prefix, days=PRUNE_DAYS, keep_file=None, dry_run=False):
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")
    today = date.today()
    cutoff_days = int(days)
    removed = []
    pattern = f"{prefix}_*.json"
    #print(f"Pruning files matching {pattern} older than {cutoff_days} days (dry_run={dry_run})")
    for fname in os.listdir(data_dir):
        if not fnmatch.fnmatch(fname, pattern):
            continue
        full = os.path.join(data_dir, fname)
        if keep_file and os.path.abspath(full) == os.path.abspath(keep_file):
            continue
        m = date_re.search(fname)
        if not m:
            continue
        try:
            file_date = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        age_days = (today - file_date).days
        if age_days > cutoff_days:
            if dry_run:
                print("[DRY] Would remove", fname, "age", age_days)
            else:
                try:
                    os.remove(full)
                    removed.append(fname)
                except Exception:
                    pass
    if removed:
        print("Deleted old files for", prefix, ":", removed)
    else:
        print("No old files deleted for", prefix)


def scrape_one_collection(prefix, collection_url, data_dir, snaps_dir):
    """Scrape one collection using Shopify JSON and save <prefix>_YYYY-MM-DD.json"""

    # ✅ GET ALL PRODUCT LINKS FROM SHOPIFY JSON
    all_links = get_product_links_shopify_json(collection_url)
    print(f"[{prefix}] Found product links:", len(all_links))

    results = []

    for i, p_url in enumerate(all_links, start=1):
        print(f"[{prefix}] [{i}/{len(all_links)}] Processing:", p_url)
        tmp = None

        try:
            tmp = download_temp(p_url)
            item = parse_product_page_from_temp(tmp, p_url)
            results.append(item)

        except Exception as e:
            pass#print("  ERROR scraping", p_url, ":", type(e).__name__, e)

        finally:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    out_filename = f"{prefix}_{datetime.now().strftime('%Y-%m-%d')}.json"
    out_path = os.path.join(data_dir, out_filename)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    prune_old_jsons(data_dir, prefix, days=PRUNE_DAYS, keep_file=out_path)

    SCRAPE_SUMMARY[prefix] = {
        "items": len(results),
        "last_modified": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    return out_path

def scrape_all_collections(selected_prefix=None):
    data_dir, snaps_dir = ensure_dirs()
    targets = COLLECTIONS.items() if selected_prefix is None else [(selected_prefix, COLLECTIONS[selected_prefix])]
    for prefix, url in targets:
        try:
            scrape_one_collection(prefix, url, data_dir, snaps_dir)
        except Exception as e:
            print("Failed scraping", prefix, url, type(e).__name__, e)

    show_summary_table()


def show_summary_table():
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    table = Table(
        title="📦 Scraping Summary (New)",
        box=box.SQUARE,
        show_lines=True
    )

    table.add_column("Category", style="cyan", justify="left")
    table.add_column("Items", style="magenta", justify="right")
    table.add_column("Last Modified", style="green", justify="center")

    for prefix, info in SCRAPE_SUMMARY.items():
        table.add_row(
            prefix.replace("_", "-").title(),
            str(info["items"]),
            info["last_modified"]
        )

    console.print(table)


if __name__ == "__main__":
    # optional command-line arg: prefix to scrape only that collection
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        if arg not in COLLECTIONS:
            print("Unknown collection prefix:", arg)
            print("Available:", list(COLLECTIONS.keys()))
            sys.exit(1)
        scrape_all_collections(selected_prefix=arg)
    else:
        scrape_all_collections()
