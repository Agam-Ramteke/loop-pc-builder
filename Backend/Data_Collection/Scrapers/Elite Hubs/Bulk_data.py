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
MAX_PAGES = 20  # max pagination pages to check for a collection


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


def get_product_links_from_collection(collection_html_path, base_url=BASE_URL):
    with open(collection_html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")
    links = []
    for a in soup.select("a[href*='/products/']"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(base_url, href.split("?")[0])
        if full not in links:
            links.append(full)
    return links


def collect_collection_pages(prefix, collection_url, snaps_dir):
    """Download paginated collection pages until no products found or MAX_PAGES reached.
    Returns list of snapshot paths saved.
    """
    snaps = []
    prev_count = 0
    for page in range(1, MAX_PAGES + 1):
        page_url = f"{collection_url}?page={page}"
        snap_path = os.path.join(snaps_dir, f"{prefix}_collection_page{page}_{datetime.now().strftime('%Y%m%d%H%M%S')}.html")
        try:
            download_to_file(page_url, snap_path)
        except Exception as e:
            # stop on network error
            try:
                if os.path.exists(snap_path):
                    os.remove(snap_path)
            except Exception:
                pass
            break
        links = get_product_links_from_collection(snap_path)
        if not links:
            # remove empty snapshot
            try:
                os.remove(snap_path)
            except Exception:
                pass
            break
        snaps.append(snap_path)
        # small heuristic: if this page returned same number of links as previous and page>1, continue anyway up to MAX_PAGES
        prev_count = len(links)
        time.sleep(random.uniform(0.4, 0.9))
    return snaps


# filename-date based pruning (deletes files like '<prefix>_YYYY-MM-DD.json' older than days)
def prune_old_jsons(data_dir, prefix, days=PRUNE_DAYS, keep_file=None, dry_run=False):
    date_re = re.compile(r"(\d{4}-\d{2}-\d{2})")
    today = date.today()
    cutoff_days = int(days)
    removed = []
    pattern = f"{prefix}_*.json"
    print(f"Pruning files matching {pattern} older than {cutoff_days} days (dry_run={dry_run})")
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
    """Scrape one collection and save <prefix>_YYYY-MM-DD.json"""
    # collect paginated snapshots
    snaps = collect_collection_pages(prefix, collection_url, snaps_dir)
    # if pagination returned nothing (maybe collection has single page without ?page=), fallback to single download
    if not snaps:
        snapshot_name = os.path.join(snaps_dir, f"{prefix}_collection_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.html")
        download_to_file(collection_url, snapshot_name)
        snaps = [snapshot_name]

    # gather product links from all snapshots
    all_links = []
    for snap in snaps:
        links = get_product_links_from_collection(snap)
        for L in links:
            if L not in all_links:
                all_links.append(L)
        # delete snapshot after extracting
        try:
            os.remove(snap)
        except Exception:
            pass

    print(f"[{prefix}] Found product links:", len(all_links))

    results = []
    for i, p_url in enumerate(all_links, start=1):
        print(f"[{prefix}] [{i}/{len(all_links)}] Processing:", p_url)
        tmp = None
        try:
            tmp = download_temp(p_url)
            item = parse_product_page_from_temp(tmp, p_url)
            results.append(item)
            print(f"  -> scraped: {item['name']}")
        except Exception as e:
            print("  ERROR scraping", p_url, ":", type(e).__name__, e)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    out_filename = f"{prefix}_{datetime.now().strftime('%Y-%m-%d')}.json"
    out_path = os.path.join(data_dir, out_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[{prefix}] Saved output to:", out_path)

    # prune old files for this prefix only (keeps the one we just wrote)
    prune_old_jsons(data_dir, prefix, days=PRUNE_DAYS, keep_file=out_path)

    return out_path


def scrape_all_collections(selected_prefix=None):
    data_dir, snaps_dir = ensure_dirs()
    targets = COLLECTIONS.items() if selected_prefix is None else [(selected_prefix, COLLECTIONS[selected_prefix])]
    for prefix, url in targets:
        try:
            scrape_one_collection(prefix, url, data_dir, snaps_dir)
        except Exception as e:
            print("Failed scraping", prefix, url, type(e).__name__, e)


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
