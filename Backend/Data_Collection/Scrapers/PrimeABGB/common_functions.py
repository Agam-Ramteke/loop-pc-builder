"""
PrimeABGB — common utility functions shared by Bulk_data.py and Async_Scraper.py.

Handles:
  • MongoDB upsert
  • Price parsing / discount calculation
  • Image downloading
  • JSON saving
  • HTML parsing for individual product pages (WooCommerce)
"""
import os
import re
import json
import logging
import hashlib
import mimetypes
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

SOURCE_NAME    = "PrimeABGB"
DEFAULT_UA     = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


# ─────────────────────────────────────────
#  PRICE UTILS
# ─────────────────────────────────────────
def parse_price_number(price_str: Optional[str]) -> Optional[float]:
    """Extract a numeric value from a string like '₹1,40,195'."""
    if not price_str:
        return None
    matches = re.findall(r"[\d,.]+", price_str)
    if not matches:
        return None
    cleaned = "".join(matches).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def calculate_discount_percent(
    original_str: Optional[str], discounted_str: Optional[str]
) -> Optional[str]:
    """Return '-30%' style string when there is a genuine discount."""
    orig = parse_price_number(original_str)
    disc = parse_price_number(discounted_str)
    if orig and disc and orig > disc:
        pct = round((1 - disc / orig) * 100)
        if pct > 0:
            return f"-{pct}%"
    return None


# ─────────────────────────────────────────
#  JSON SAVING
# ─────────────────────────────────────────
def save_json(items: list[dict], data_dir: str, prefix: str) -> str:
    """Save items to a dated JSON file and return the path."""
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{prefix}_{today}.json"
    path     = os.path.join(data_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2, default=str)
    log.info("Saved %d items → %s", len(items), path)
    return path


# ─────────────────────────────────────────
#  IMAGE DOWNLOADING
# ─────────────────────────────────────────
def _url_to_filename(image_url: str, product_url: Optional[str] = None) -> str:
    """Derive a stable local filename from an image URL."""
    parsed = urlparse(image_url)
    base   = os.path.basename(parsed.path)
    if base and "." in base:
        return base
    # Fallback: hash the URL
    h = hashlib.md5((product_url or image_url).encode()).hexdigest()[:12]
    ext = mimetypes.guess_extension(
        mimetypes.guess_type(image_url)[0] or "image/jpeg"
    ) or ".jpg"
    return f"{h}{ext}"


def download_image(
    image_url: str,
    folder: str,
    product_url: Optional[str] = None,
    collection=None,
    db_filter: Optional[dict] = None,
) -> Optional[str]:
    """Download an image and return the local path. Skips if already cached."""
    if not image_url:
        return None

    os.makedirs(folder, exist_ok=True)
    filename   = _url_to_filename(image_url, product_url)
    local_path = os.path.join(folder, filename)

    if os.path.exists(local_path):
        return local_path

    try:
        resp = requests.get(
            image_url,
            headers={"User-Agent": DEFAULT_UA, "Referer": "https://www.primeabgb.com/"},
            timeout=20,
            stream=True,
        )
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)

        # Optionally update MongoDB with local path
        if collection is not None and db_filter:
            collection.update_one(db_filter, {"$set": {"image_path": local_path}}, upsert=False)

        log.debug("Image saved: %s", local_path)
        return local_path

    except Exception as exc:
        log.warning("Image download failed (%s): %s", image_url, exc)
        return None


# ─────────────────────────────────────────
#  MONGODB UPSERT
# ─────────────────────────────────────────
def upsert_product(collection, data: dict) -> None:
    """
    Upsert a product into MongoDB by URL.

    Strategy:
    • Uses $setOnInsert for fields that should only be set on first insert.
    • Uses $set for fields that should always be refreshed.
    • IMPORTANT: Only overwrites the price sub-document when the parsed
      prices are non-null, to avoid clobbering valid Bulk_data prices.
    """
    url = data.get("url")
    if not url:
        log.warning("upsert_product: skipping record with no URL")
        return

    price = data.get("price", {})

    # Build the $set payload — refresh everything except price initially
    set_fields: dict = {
        "name":         data.get("name"),
        "scraped_at":   data.get("scraped_at", datetime.now(timezone.utc)),
        "stock_status": data.get("stock_status"),
        "source":       data.get("source", SOURCE_NAME),
    }
    if data.get("image_path"):
        set_fields["image_path"] = data["image_path"]
    if data.get("image_url"):
        set_fields["image_url"] = data["image_url"]
    if data.get("specifications"):
        set_fields["specifications"] = data["specifications"]

    # Only write price fields that are non-null so we don't overwrite
    # good Bulk_data prices with nulls from the product-page parse.
    if price.get("discounted"):
        set_fields["price.discounted"] = price["discounted"]
    if price.get("original"):
        set_fields["price.original"] = price["original"]
    if price.get("discount"):
        set_fields["price.discount"] = price["discount"]

    # Compute discount % if missing
    if not price.get("discount") and price.get("original") and price.get("discounted"):
        disc = calculate_discount_percent(price["original"], price["discounted"])
        if disc:
            set_fields["price.discount"] = disc

    collection.update_one(
        {"url": url},
        {
            "$set":         set_fields,
            "$setOnInsert": {"url": url},
        },
        upsert=True,
    )


# ─────────────────────────────────────────
#  HTML PARSING — PRODUCT PAGE (WooCommerce)
# ─────────────────────────────────────────
def parse_product_page(
    html_file_path: str,
    product_url: Optional[str] = None,
    image_url: Optional[str] = None,
    collection=None,
    image_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse a PrimeABGB product detail page (saved HTML snapshot).
    Returns a dict ready for upsert_product().

    Selectors (WooCommerce):
      name:          h1.product_title.entry-title
      sale price:    .summary .price ins .woocommerce-Price-amount bdi
      original:      .summary .price del .woocommerce-Price-amount bdi
      regular price: .summary .price > .woocommerce-Price-amount bdi  (no discount)
      stock:         p.stock
      specs:         table.woocommerce-product-attributes.shop_attributes tr
      image:         .woocommerce-product-gallery__image img (data-large_image or src)
    """
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # ── Name ──
    name_el = soup.select_one("h1.product_title.entry-title")
    name    = name_el.get_text(strip=True) if name_el else None

    # ── Prices ──
    summary = soup.select_one("div.summary.entry-summary")
    price_el = summary.select_one(".price") if summary else None

    sale_el     = price_el.select_one("ins .woocommerce-Price-amount bdi") if price_el else None
    original_el = price_el.select_one("del .woocommerce-Price-amount bdi") if price_el else None
    regular_el  = (
        price_el.select_one(".woocommerce-Price-amount bdi")
        if price_el and not sale_el
        else None
    )

    sale_str     = sale_el.get_text(strip=True)     if sale_el     else None
    original_str = original_el.get_text(strip=True) if original_el else None
    # If no sale/original, a single "regular" price exists
    regular_str  = regular_el.get_text(strip=True)  if regular_el  else None

    parsed_prices = {
        "discounted": sale_str or regular_str,
        "original":   original_str,
        "discount":   None,
    }

    # Fallback from existing DB if product-page parse found nothing
    existing_price: Dict[str, Any] = {}
    if collection is not None and product_url:
        try:
            existing_doc = collection.find_one({"url": product_url}, {"price": 1})
            if existing_doc and isinstance(existing_doc.get("price"), dict):
                existing_price = existing_doc["price"]
        except Exception as exc:
            log.warning("DB fallback fetch failed: %s", exc)

    prices = {
        "discounted": parsed_prices["discounted"] or existing_price.get("discounted"),
        "original":   parsed_prices["original"]   or existing_price.get("original"),
        "discount":   existing_price.get("discount"),
    }

    # Auto-calculate discount %
    if not prices["discount"] and prices["original"] and prices["discounted"]:
        prices["discount"] = calculate_discount_percent(prices["original"], prices["discounted"])

    # ── Stock ──
    stock_el     = soup.select_one("p.stock")
    stock_status = stock_el.get_text(strip=True) if stock_el else None

    # ── Specifications ──
    # Priority 1: Spec table inside the Description tab (the "Specification:" section in the screenshot)
    # PrimeABGB renders a 2-column <table> inside .entry-content.wc-tab (the description panel)
    specifications: Dict[str, str] = {}

    desc_tab = soup.select_one(".woocommerce-Tabs-panel--description, #tab-description, .entry-content.wc-tab")
    if desc_tab:
        for tbl in desc_tab.select("table"):
            rows = tbl.select("tr")
            if len(rows) < 2:
                continue
            # Only process tables whose rows have exactly 2 cells (label + value)
            valid = True
            for row in rows[:3]:
                cells = row.select("td, th")
                if len(cells) != 2:
                    valid = False
                    break
            if not valid:
                continue
            # This is our spec table
            for row in rows:
                cells = row.select("td, th")
                if len(cells) == 2:
                    key = cells[0].get_text(separator=" ", strip=True)
                    val = cells[1].get_text(separator=" ", strip=True)
                    if key:
                        specifications[key] = val
            if specifications:
                break  # Stop after the first valid spec table

    # Priority 2: Fallback — WooCommerce Additional Information tab table
    if not specifications:
        for row in soup.select("table.woocommerce-product-attributes.shop_attributes tr"):
            label_el = row.select_one("th.woocommerce-product-attributes-item__label")
            value_el = row.select_one("td.woocommerce-product-attributes-item__value")
            if label_el and value_el:
                specifications[label_el.get_text(strip=True)] = value_el.get_text(strip=True)

    # ── Image ──
    local_image_path = None
    try:
        resolved_image_url = image_url
        if not resolved_image_url:
            img_el = soup.select_one(".woocommerce-product-gallery__image img")
            if img_el:
                resolved_image_url = (
                    img_el.get("data-large_image")
                    or img_el.get("data-src")
                    or img_el.get("src")
                )

        if resolved_image_url and image_dir:
            local_image_path = download_image(
                resolved_image_url,
                folder=image_dir,
                product_url=product_url,
                collection=collection,
                db_filter={"url": product_url} if product_url else None,
            )
    except Exception as exc:
        log.warning("Image download failed for %s: %s", product_url, exc)

    return {
        "name":           name,
        "url":            product_url,
        "image_path":     local_image_path,
        "price":          prices,
        "stock_status":   stock_status,
        "specifications": specifications,
        "source":         SOURCE_NAME,
        "scraped_at":     datetime.now(timezone.utc),
    }
