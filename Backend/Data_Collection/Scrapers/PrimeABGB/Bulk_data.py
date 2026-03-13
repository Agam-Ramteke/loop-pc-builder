"""
PrimeABGB — Bulk category scraper.

Scrapes all product listing pages (pagination handled automatically) for each
configured category and saves them as dated JSON files in the `data/` directory.

Run:
    python Bulk_data.py

This is the first step in the pipeline — it populates `data/*.json` with product
URLs, names, images, and prices from the listing pages. The Async_Scraper then
uses these URLs to fetch individual product pages for full specs.
"""
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
from rich.table import Table
from rich.console import Console
from rich.theme import Theme

import common_functions as cf

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Category slug → catalog URL mapping for PrimeABGB (WooCommerce)
CATEGORIES = {
    "processor":      "https://www.primeabgb.com/buy-online-price-india/cpu-processor/",
    "graphics-card":  "https://www.primeabgb.com/buy-online-price-india/graphic-cards-gpu/",
    "ram":            "https://www.primeabgb.com/buy-online-price-india/ram-memory/",
    "ssd":            "https://www.primeabgb.com/buy-online-price-india/ssd/",
    "hdd":            "https://www.primeabgb.com/buy-online-price-india/internal-hard-drive/",
    "motherboard":    "https://www.primeabgb.com/buy-online-price-india/motherboards/",
    "smps":           "https://www.primeabgb.com/buy-online-price-india/power-supplies-smps/",
    "cabinet":        "https://www.primeabgb.com/buy-online-price-india/pc-cases-cabinet/",
    "cpu-cooler":     "https://www.primeabgb.com/buy-online-price-india/cpu-cooler/",
}

CHROME_IMPERSONATE = "chrome"
REQUEST_TIMEOUT    = 30

# ─────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

console = Console(theme=Theme({"repr.str": "none"}), color_system="auto", force_terminal=False)
SUPPORTS_COLOR = console.is_terminal


# ─────────────────────────────────────────
#  PARSER — category listing page
# ─────────────────────────────────────────
def parse_listing_page(html_content: str, base_url: str) -> list[dict]:
    """
    Extract product cards from a WooCommerce category listing page.

    WooCommerce selectors:
      products:       ul.products > li.product
      name:           h2.woocommerce-loop-product__title
      link:           a.woocommerce-LoopProduct-link[href]
      image:          a.woocommerce-LoopProduct-link img[data-lazy-src | src]
      sale price:     .price ins .woocommerce-Price-amount bdi
      original price: .price del .woocommerce-Price-amount bdi
      regular price:  .price > .woocommerce-Price-amount bdi   (when no discount)
    """
    soup  = BeautifulSoup(html_content, "html.parser")
    items = []

    for product in soup.select(".product"):
        # Name
        name_el = product.select_one("h2.woocommerce-loop-product__title, h3, .product-title")
        name    = name_el.get_text(strip=True) if name_el else None

        # URL
        link_el = product.select_one("a.woocommerce-LoopProduct-link") or product.select_one("a")
        url     = link_el["href"].strip() if link_el and link_el.has_attr("href") else None

        # Image — prefer lazy-loaded src, fall back to src
        image_url = None
        img_el = product.select_one("a.woocommerce-LoopProduct-link img")
        if img_el:
            image_url = (
                img_el.get("data-lazy-src")
                or img_el.get("data-src")
                or img_el.get("src")
            )
            # Filter out base64 placeholders
            if image_url and image_url.startswith("data:"):
                image_url = img_el.get("data-lazy-src") or img_el.get("data-src")

        # Prices
        price_el    = product.select_one(".price")
        sale_el     = price_el.select_one("ins .woocommerce-Price-amount bdi") if price_el else None
        original_el = price_el.select_one("del .woocommerce-Price-amount bdi") if price_el else None

        # When there's no discount the price is a bare .woocommerce-Price-amount bdi
        regular_el  = (
            price_el.select_one(".woocommerce-Price-amount bdi")
            if price_el and not sale_el
            else None
        )

        sale_str     = sale_el.get_text(strip=True)     if sale_el     else None
        original_str = original_el.get_text(strip=True) if original_el else None
        regular_str  = regular_el.get_text(strip=True)  if regular_el  else None

        discounted = sale_str or regular_str
        original   = original_str

        discount = None
        if original and discounted:
            discount = cf.calculate_discount_percent(original, discounted)
            
        # Filter out external/portable drives (applies to HDD/SSD categories)
        n_lower = name.lower() if name else ""
        if "external" in n_lower or "portable" in n_lower:
            continue

        items.append({
            "name":      name,
            "url":       url,
            "image_url": image_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "price": {
                "original":   original,
                "discounted": discounted,
                "discount":   discount,
            },
            "stock_status":   None,
            "specifications": {},
            "source": cf.SOURCE_NAME,
        })

    return items


# ─────────────────────────────────────────
#  FETCHER
# ─────────────────────────────────────────
async def fetch_page(session: AsyncSession, url: str, retries: int = 3) -> str | None:
    """Fetch a page using curl_cffi Chrome impersonation with exponential back-off."""
    for attempt in range(1, retries + 1):
        try:
            resp = await session.get(url, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 200:
                return resp.text

            if resp.status_code in (403, 429):
                wait = 2 ** attempt
                log.warning("HTTP %d for %s — attempt %d/%d, backing off %ds",
                            resp.status_code, url, attempt, retries, wait)
                await asyncio.sleep(wait)
                continue

            log.warning("HTTP %d for %s (not retrying)", resp.status_code, url)
            return None

        except asyncio.TimeoutError:
            log.error("Timeout fetching %s (attempt %d/%d)", url, attempt, retries)
        except Exception as exc:
            log.error("Error fetching %s: %s (attempt %d/%d)", url, exc, attempt, retries)

        if attempt < retries:
            await asyncio.sleep(1.5 * attempt)

    log.error("Giving up on %s after %d attempts.", url, retries)
    return None


# ─────────────────────────────────────────
#  SCRAPER — one category
# ─────────────────────────────────────────
async def scrape_category(
    session: AsyncSession,
    slug: str,
    base_url: str,
) -> tuple[str, int]:
    """Scrape all listing pages for a category. Returns (slug, total_items)."""
    all_items: list[dict] = []
    page = 1

    while True:
        # WooCommerce pagination: /category-slug/page/2/
        if page == 1:
            page_url = base_url
        else:
            # Ensure trailing slash before /page/
            page_url = base_url.rstrip("/") + f"/page/{page}/"

        html = await fetch_page(session, page_url)
        if not html:
            break

        page_items = parse_listing_page(html, base_url)
        if not page_items:
            log.info("  %s — page %d returned 0 items, stopping", slug, page)
            break

        all_items.extend(page_items)
        log.info("  %s — page %d: %d items (total %d)", slug, page, len(page_items), len(all_items))

        # Check for next page link
        soup = BeautifulSoup(html, "html.parser")
        if not soup.select_one("a.next.page-numbers"):
            break

        page += 1
        await asyncio.sleep(0.8)   # polite crawl delay

    if all_items:
        # Deduplicate before saving (WooCommerce can sometimes repeat items across pages)
        seen_urls = set()
        seen_names = set()
        unique_items = []
        
        for item in all_items:
            url = item.get("url")
            name = item.get("name")
            
            if (url and url in seen_urls) or (name and name in seen_names):
                continue
                
            if url: seen_urls.add(url)
            if name: seen_names.add(name)
            unique_items.append(item)
            
        cf.save_json(unique_items, DATA_DIR, prefix=slug)

    return slug, len(all_items)


# ─────────────────────────────────────────
#  SUMMARY TABLE
# ─────────────────────────────────────────
def show_summary_table(title: str, data_dict: dict) -> None:
    table = Table(title=title, show_lines=True)
    cols = ["Category", "Items", "Last Modified"]
    for col in cols:
        table.add_column(col, justify="left" if col == "Category" else "right")
    for cat, info in sorted(data_dict.items()):
        table.add_row(cat.capitalize(), str(info["count"]), info["date"])
    console.print(table)


# ─────────────────────────────────────────
#  DUPLICATE CHECKER
# ─────────────────────────────────────────
async def check_for_duplicates() -> None:
    """Check for duplicate products within the JSON files in DATA_DIR. Runs asynchronously."""
    console.print("\n[bold cyan]Checking for duplicates in JSON files...[/]")
    
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    if not json_files:
        console.print("[yellow]No JSON files found to check.[/]")
        return
        
    total_dupes = 0
    loop = asyncio.get_event_loop()
    
    for f in sorted(json_files):
        file_path = os.path.join(DATA_DIR, f)
        
        # Read file asynchronously to not block the event loop
        try:
            with open(file_path, "r", encoding="utf-8") as jf:
                data = await loop.run_in_executor(None, json.load, jf)
        except Exception as exc:
            log.warning("Could not read %s: %s", f, exc)
            continue
            
        seen_urls = set()
        seen_names = set()
        dupes = 0
        
        for item in data:
            url = item.get("url")
            name = item.get("name")
            
            is_dupe = False
            if url and url in seen_urls:
                is_dupe = True
            elif name and name in seen_names:
                is_dupe = True
                
            if is_dupe:
                dupes += 1
            else:
                if url: seen_urls.add(url)
                if name: seen_names.add(name)
                
        if dupes > 0:
            console.print(f"[yellow]  ⚠️ {f}: Found {dupes} duplicates out of {len(data)} items.[/]")
            total_dupes += dupes
        else:
            console.print(f"[green]  ✅ {f}: No duplicates found ({len(data)} items).[/]")
            
    if total_dupes > 0:
        console.print(f"\n[bold yellow]Found {total_dupes} total duplicates across all files.[/]\n")
    else:
        console.print("\n[bold green]No duplicates found in any files! 🎉[/]\n")


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
async def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Skip categories already scraped today
    existing_slugs: set[str] = set()
    for f in os.listdir(DATA_DIR):
        if f.endswith(".json") and today in f:
            existing_slugs.add(Path(f).stem.rsplit("_", 1)[0])

    pending = {slug: url for slug, url in CATEGORIES.items() if slug not in existing_slugs}

    async with AsyncSession(impersonate=CHROME_IMPERSONATE) as session:
        if pending:
            console.print(f"\n[bold cyan]PrimeABGB Scraper[/] — {len(pending)} categories to scrape\n")
            tasks   = [asyncio.create_task(scrape_category(session, slug, url))
                       for slug, url in pending.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            scraped: dict[str, dict] = {}
            for (slug, _), result in zip(pending.items(), results):
                if isinstance(result, Exception):
                    log.error("Category %s failed: %s", slug, result)
                    continue
                cat_name, count = result
                scraped[cat_name] = {
                    "count": count,
                    "date":  datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                }

            if scraped:
                show_summary_table("PrimeABGB Scraping Summary", scraped)
        else:
            # Show existing data
            existing_data: dict[str, dict] = {}
            for f in sorted(os.listdir(DATA_DIR)):
                if not f.endswith(".json"):
                    continue
                fp = os.path.join(DATA_DIR, f)
                try:
                    with open(fp, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    cat  = Path(f).stem.rsplit("_", 1)[0]
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(fp), tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M")
                    existing_data[cat] = {"count": len(data), "date": mtime}
                except Exception as exc:
                    log.warning("Could not read %s: %s", f, exc)

            if existing_data:
                show_summary_table("PrimeABGB — Existing Data", existing_data)
                console.print("[green]All categories already scraped today.[/]")
            else:
                console.print("[yellow]No data found in data/ directory.[/]")

    # Check for duplicates after all scraping is done
    await check_for_duplicates()


if __name__ == "__main__":
    asyncio.run(main())
