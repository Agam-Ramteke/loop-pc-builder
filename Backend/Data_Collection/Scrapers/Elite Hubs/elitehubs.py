"""
elitehubs.py
Download collection page -> parse product links -> download each product page temporarily
Parse fields into JSON matching your boyfriend's format and save to Elite Hubs/data/.
"""

import requests
import tempfile
import os
import time
import json
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
# ---------- CONFIG ----------
COLLECTION_URL = "https://www.elitehubs.com/collections/processor"
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
# --------------------------------

def ensure_dirs():
    """Return paths to Elite Hubs/data and Elite Hubs/async_snapshots (create if missing)."""
    base = os.path.abspath(os.path.dirname(__file__))  # Elite Hubs folder
    data_dir = os.path.join(base, "data")
    snaps_dir = os.path.join(base, "async_snapshots")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(snaps_dir, exist_ok=True)
    return data_dir, snaps_dir

def download_to_file(url, dest_path, timeout=20):
    """Download URL and save the response.text to dest_path."""
    print("Downloading:", url)
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(r.text)
    return dest_path

def download_temp(url, timeout=20):
    """Download the URL, write to a temp file, and return the temp path."""
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    fd, path = tempfile.mkstemp(suffix=".html", text=True)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(r.text)
    return path

def parse_product_page_from_temp(temp_path, url):
    """Parse a product HTML file saved in temp_path and return a dict matching the desired JSON schema."""
    with open(temp_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "lxml")

    def meta(prop):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    # Primary fields (OG meta tags are present on EliteHubs pages)
    title = meta("og:title") or (soup.title.string.strip() if soup.title else None)
    image = meta("og:image:secure_url") or meta("og:image")
    price_amount = meta("og:price:amount")  # may be single current price
    currency = meta("og:price:currency")

    # Some stores show both original & discounted price in HTML; try to detect:
    original_price = None
    discounted_price = None

    # Try to find price on page in visible HTML (fallback heuristics)
    # Find any element that looks like a crossed original price or "compare-at" class
    # These are best-effort; if not found, set original==discounted==price_amount
    if price_amount:
        discounted_price = price_amount

    # Check for typical 'compare at' or 'price--compare' classes (common in themes)
    # We'll inspect <span> tags that contain currency symbol and numbers
    text = soup.get_text(" ", strip=True)
    # simple stock detection
    stock_status = None
    txt_lower = text.lower()
    if "out of stock" in txt_lower or "sold out" in txt_lower:
        stock_status = "Out of Stock"
    elif "in stock" in txt_lower:
        stock_status = "In Stock"

    # Try to detect an original price in the product page (best-effort)
    # Look for elements that include "compare" or "original" keywords
    compare_candidates = soup.select("[class*='compare'], [class*='original'], [class*='was-price'], [class*='price--compare']")
    for el in compare_candidates:
        s = el.get_text(" ", strip=True)
        if s and any(ch.isdigit() for ch in s):
            original_price = s
            break

    # If we didn't find original price, try a second heuristic: search for the first two price-like strings on page
    if not original_price:
        import re
        prices = re.findall(r"₹\s?[0-9,]+(?:\.\d+)?", text)
        if prices:
            if len(prices) >= 2:
                original_price, discounted_price = prices[0], prices[1]
            else:
                # single price on page
                if not discounted_price:
                    discounted_price = prices[0]
                if not original_price:
                    original_price = prices[0]

    # Final fallback: set original==discounted if only one price found
    if not original_price and discounted_price:
        original_price = discounted_price
    if not discounted_price and original_price:
        discounted_price = original_price

    # Clean small strings
    def clean(x):
        return x.strip() if isinstance(x, str) and x.strip() else None

    obj = {
        "name": clean(title),
        "url": url,
        "image_url": clean(image),
        "scraped_at": datetime.utcnow().isoformat(),
        "price": {
            "original": clean(original_price),
            "discounted": clean(discounted_price),
            "discount": None
        },
        "stock_status": stock_status,
        "specifications": {},  # we'll leave empty for now (can add parser later)
        "source": "EliteHubs"
    }
    return obj

def get_product_links_from_collection(collection_html_path, base_url=BASE_URL):
    """Parse the saved collection HTML and return absolute product URLs (unique)."""
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

def scrape_processors():
    data_dir, snaps_dir = ensure_dirs()

    # Step A: download collection page to snapshot file (so you have a saved copy)
    today = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    collection_snapshot = os.path.join(snaps_dir, f"processors_collection_{today}.html")
    download_to_file(COLLECTION_URL, collection_snapshot)

    # Step B: get product links from snapshot
    product_links = get_product_links_from_collection(collection_snapshot)
    print("Found product links:", len(product_links))

    results = []
    for i, p_url in enumerate(product_links, start=1):
        print(f"[{i}/{len(product_links)}] Processing:", p_url)
        tmp = None
        try:
            # download product page to a temporary file
            tmp = download_temp(p_url)
            # parse product page from temp file
            item = parse_product_page_from_temp(tmp, p_url)
            results.append(item)
            print("  -> scraped:", item["name"])
        except Exception as e:
            print("  ERROR scraping", p_url, ":", type(e).__name__, e)
        finally:
            # delete temp file immediately
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

        # polite delay between product requests
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    # Step C: Save results to Elite Hubs/data/ (now uses data_dir from ensure_dirs)
    out_filename = f"processors_{datetime.now().strftime('%Y-%m-%d')}.json"
    out_path = os.path.join(data_dir, out_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print("Saved output to:", out_path)
    return out_path

if __name__ == "__main__":
    scrape_processors()
