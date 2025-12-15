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
async def scrape_category(session, base_url):
    """Scrape all pages in a category and save to JSON."""
    category_name = Path(urlparse(base_url).path).name
    all_items = []
    page = 1

    while True:
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
        await asyncio.sleep(0.6)

    if all_items:
        cf.save_json(all_items, DATA_DIR, prefix=category_name)
        return category_name, len(all_items)
    else:
        return category_name, 0


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


# -------------------------- MAIN --------------------------
async def main():
    today = datetime.now().strftime("%Y-%m-%d")

    existing_files = {
        "_".join(f.split("_")[:-1]): f
        for f in os.listdir(DATA_DIR)
        if f.endswith(".json") and today in f
    }

    scraped_today = {}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=10)) as session:
        tasks = []
        for link in URLS:
            cat = Path(urlparse(link).path).name
            if cat in existing_files:
                continue
            tasks.append(asyncio.create_task(scrape_category(session, link)))

        if tasks:
            console.print(f"\n🚀 Starting {len(tasks)} async category scrapes...\n")
            results = await asyncio.gather(*tasks)

            for cat, count in results:
                scraped_today[cat] = {
                    "count": count,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }

            show_summary_table("📦 Scraping Summary (New)", scraped_today)

        else:
            existing_data = {}
            for f in sorted(os.listdir(DATA_DIR)):
                if f.endswith(".json"):
                    file_path = os.path.join(DATA_DIR, f)
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


if __name__ == "__main__":
    asyncio.run(main())
