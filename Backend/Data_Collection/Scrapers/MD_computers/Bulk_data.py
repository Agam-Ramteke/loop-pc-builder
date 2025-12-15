import os
import json
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path
from rich.table import Table
from rich.console import Console
from rich.theme import Theme
import argparse
import signal
import sys
import common_functions as cf

# --- SETTINGS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

URLS = [
    "https://mdcomputers.in/catalog/processor",
    "https://mdcomputers.in/catalog/graphics-card",
    "https://mdcomputers.in/catalog/ram",
    "https://mdcomputers.in/catalog/storage",
    "https://mdcomputers.in/catalog/smps",
    "https://mdcomputers.in/catalog/cabinet",
    "https://mdcomputers.in/catalog/cpu-cooler"
]


HEADERS = {"User-Agent": UserAgent().random}
os.makedirs(DATA_DIR, exist_ok=True)

# --- Console Setup ---
console = Console(theme=Theme({"repr.str": "none"}), color_system="auto", force_terminal=False)
SUPPORTS_COLOR = console.is_terminal

_shutdown = False


def _on_term(signum, frame):
    global _shutdown
    _shutdown = True
    print("\nReceived shutdown signal — will stop after current page.")


# -------------------------- PARSER --------------------------
def parse_snapshot(html_content):
    """Extract product data from an HTML page."""
    soup = BeautifulSoup(html_content, "html.parser")
    items = []

    for product in soup.select("div.product-grid-item"):
        name_el = product.select_one("h3.product-entities-title a")
        name = name_el.get_text(strip=True) if name_el else None
        url = name_el["href"].strip() if name_el and name_el.has_attr("href") else None

        image_el = product.select_one("img")
        image_url = (
            image_el.get("src")
            or image_el.get("data-src")
            or image_el.get("data-lazy-src")
            or image_el.get("data-cfsrc")
            if image_el else None
        )
        if image_url and image_url.startswith("/"):
            image_url = "https://mdcomputers.in" + image_url

        price_del = product.select_one("span.price span.del")
        price_ins = product.select_one("span.price span.ins")

        items.append({
            "name": name,
            "url": url,
            "image_url": image_url,
            "scraped_at": datetime.now().isoformat(),
            "price": {
                "original": price_del.get_text(strip=True) if price_del else None,
                "discounted": price_ins.get_text(strip=True) if price_ins else None,
                "discount": None
            },
            "stock_status": None,
            "specifications": {},
            "source": "MD Computers"
        })

    return items


# -------------------------- FETCHER --------------------------
async def fetch_page(session, url):
    """Download page asynchronously."""
    try:
        async with session.get(url, headers=HEADERS, timeout=20) as resp:
            if resp.status == 200:
                return await resp.text()
    except Exception:
        return None
    return None


# -------------------------- SCRAPER --------------------------
async def scrape_category(session, base_url, page_limit=None):
    """Scrape all pages in a category and return items list and metadata."""
    global _shutdown
    category_name = Path(urlparse(base_url).path).name
    all_items = []
    page = 1

    while True:
        if _shutdown:
            print("Shutdown requested — stopping scraping this category.")
            break

        page_url = base_url if page == 1 else f"{base_url}?page={page}"
        html = await fetch_page(session, page_url)
        if not html:
            break

        page_items = parse_snapshot(html)
        if not page_items:
            break

        all_items.extend(page_items)

        soup = BeautifulSoup(html, "html.parser")
        has_next = bool(soup.find("link", rel="next"))
        if not has_next:
            break

        page += 1
        if page_limit and page > page_limit:
            break
        await asyncio.sleep(0.6)

    return category_name, all_items


# -------------------------- SUMMARY TABLE --------------------------
def show_summary_table(title, data_dict):
    """Display a summary table — clean even if colors unsupported."""
    if SUPPORTS_COLOR:
        table = Table(title=title, show_lines=True)
        table.add_column("Category", justify="left", style="cyan")
        table.add_column("Items", justify="right", style="green")
        table.add_column("Last Modified", justify="right", style="yellow")
    else:
        table = Table(title=title, show_lines=True)
        table.add_column("Category", justify="left")
        table.add_column("Items", justify="right")
        table.add_column("Last Modified", justify="right")

    for category, info in sorted(data_dict.items()):
        table.add_row(category.capitalize(), str(info["count"]), info["date"])

    console.print(table)


# -------------------------- Core runner --------------------------
async def run_categories(urls, data_dir=DATA_DIR, skip_existing=True, page_limit=None):
    """Run scraping for given category URLs. Returns summary dict."""
    global _shutdown
    today = datetime.now().strftime("%Y-%m-%d")

    existing_files = {
        "_".join(f.split("_")[:-1]): f
        for f in os.listdir(data_dir)
        if f.endswith(".json") and today in f
    }

    scraped_today = {}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        tasks = []
        for link in urls:
            cat = Path(urlparse(link).path).name
            if skip_existing and cat in existing_files:
                continue
            tasks.append(asyncio.create_task(scrape_category(session, link, page_limit=page_limit)))

        if tasks:
            print(f"\n🚀 Starting {len(tasks)} async category scrapes...\n")
            results = await asyncio.gather(*tasks)

            for cat, items in results:
                if _shutdown:
                    print("Shutdown requested — aborting saving of remaining categories.")
                    break
                if items:
                    # save JSON via common_functions helper
                    cf.save_json(items, data_dir, prefix=cat)
                    scraped_today[cat] = {"count": len(items), "date": datetime.now().strftime("%Y-%m-%d %H:%M")}

            if scraped_today:
                show_summary_table("📦 Scraping Summary (New)", scraped_today)

        else:
            # Nothing to scrape — show existing data summary
            existing_data = {}
            for f in sorted(os.listdir(data_dir)):
                if f.endswith(".json"):
                    file_path = os.path.join(data_dir, f)
                    try:
                        with open(file_path, "r", encoding="utf-8") as jf:
                            data = json.load(jf)
                        category = f.split("_")[0]
                        item_count = len(data)
                        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M")
                        existing_data[category] = {"count": item_count, "date": modified_time}
                    except Exception:
                        pass

            if existing_data:
                show_summary_table("📁 Existing Scraped Data", existing_data)
                print("✅ All categories already scraped today.\n")
            else:
                print("⚠️ No existing data found in directory.\n")


# -------------------------- CLI wrapper --------------------------
def cli_entry():
    parser = argparse.ArgumentParser(description="MD_computers bulk scraper (headless)")
    parser.add_argument("--categories", "-c", help="Comma-separated category slugs to scrape (e.g. processor,ram)")
    parser.add_argument("--all", action="store_true", help="Scrape all configured categories (default)")
    parser.add_argument("--skip-existing", dest="skip_existing", action="store_true", default=True,
                        help="Skip categories already scraped today (default)")
    parser.add_argument("--no-skip", dest="skip_existing", action="store_false", help="Do not skip existing files")
    parser.add_argument("--page-limit", type=int, default=None, help="Limit number of pages per category (for testing)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _on_term)
    signal.signal(signal.SIGTERM, _on_term)

    if args.categories:
        requested = [s.strip() for s in args.categories.split(",") if s.strip()]
        urls = [u for u in URLS if Path(urlparse(u).path).name in requested]
        if not urls:
            print("No matching categories found for those slugs.")
            return
    else:
        urls = URLS if args.all or not args.categories else []

    try:
        asyncio.run(run_categories(urls, data_dir=DATA_DIR, skip_existing=args.skip_existing, page_limit=args.page_limit))
    except Exception as e:
        print(f"Fatal error during run: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    cli_entry()
