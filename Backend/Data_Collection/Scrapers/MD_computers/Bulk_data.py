import os
import json
import asyncio
import logging
from curl_cffi.requests import AsyncSession   # replaces aiohttp for page fetching
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urlparse
from datetime import datetime, timezone
from pathlib import Path
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

URLS = [
    "https://mdcomputers.in/catalog/processor",
    "https://mdcomputers.in/catalog/graphics-card",
    "https://mdcomputers.in/catalog/ram",
    "https://mdcomputers.in/catalog/storage",
    "https://mdcomputers.in/catalog/smps",
    "https://mdcomputers.in/catalog/cabinet",
    "https://mdcomputers.in/catalog/cpu-cooler",
]

# curl_cffi impersonates Chrome at the TLS level — no extra headers needed.
# aiohttp was blocked because Python's SSL stack has a different TLS fingerprint
# than a real browser; the server detects that before even reading headers.
CHROME_IMPERSONATE = "chrome"
REQUEST_TIMEOUT    = 30   # seconds

# ─────────────────────────────────────────
#  LOGGING
# ─────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  CONSOLE
# ─────────────────────────────────────────
console = Console(theme=Theme({"repr.str": "none"}), color_system="auto", force_terminal=False)
SUPPORTS_COLOR = console.is_terminal

# UserAgent instantiated once — UA init downloads a DB, doing it per-call is slow
try:
    _ua = UserAgent()
    def _random_ua() -> str:
        return _ua.random
except Exception:
    def _random_ua() -> str:   # type: ignore[misc]
        return cf.DEFAULT_USER_AGENT


# ─────────────────────────────────────────
#  PARSER
# ─────────────────────────────────────────
def parse_snapshot(html_content: str) -> list[dict]:
    """Extract product listing data from a category page HTML."""
    soup  = BeautifulSoup(html_content, "html.parser")
    items = []

    for product in soup.select("div.product-grid-item"):
        name_el = product.select_one("h3.product-entities-title a")
        name    = name_el.get_text(strip=True) if name_el else None
        url     = name_el["href"].strip() if name_el and name_el.has_attr("href") else None

        image_url = None
        image_el  = product.select_one("img")
        if image_el:
            image_url = (
                image_el.get("src")
                or image_el.get("data-src")
                or image_el.get("data-lazy-src")
                or image_el.get("data-cfsrc")
            )
        if image_url and image_url.startswith("/"):
            image_url = "https://mdcomputers.in" + image_url

        price_del = product.select_one("span.price span.del")
        price_ins = product.select_one("span.price span.ins")

        items.append({
            "name":      name,
            "url":       url,
            "image_url": image_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "price": {
                "original":   price_del.get_text(strip=True) if price_del else None,
                "discounted": price_ins.get_text(strip=True) if price_ins else None,
                "discount":   None,
            },
            "stock_status":   None,
            "specifications": {},
            "source": "MD Computers",
        })

    return items


# ─────────────────────────────────────────
#  FETCHER
# ─────────────────────────────────────────
async def fetch_page(
    session: AsyncSession,
    url: str,
    retries: int = 3,
) -> str | None:
    """
    Fetch a page using curl_cffi (Chrome TLS impersonation).

    curl_cffi replicates Chrome's exact TLS handshake (JA3 fingerprint, ALPN,
    cipher suites) so Cloudflare and similar WAFs cannot distinguish it from a
    real browser at the network layer.  On 403/429 we back off exponentially and
    rotate the User-Agent before retrying.
    """
    for attempt in range(1, retries + 1):
        headers = {"User-Agent": _random_ua()}
        try:
            resp = await session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 200:
                return resp.text

            if resp.status_code in (403, 429):
                wait = 2 ** attempt          # 2 → 4 → 8 s
                log.warning(
                    "HTTP %d for %s — attempt %d/%d, retrying in %ds",
                    resp.status_code, url, attempt, retries, wait,
                )
                await asyncio.sleep(wait)
                continue

            # 404, 500, … — no point retrying
            log.warning("HTTP %d for %s (not retrying)", resp.status_code, url)
            return None

        except asyncio.TimeoutError:
            log.error("Timeout fetching %s (attempt %d/%d)", url, attempt, retries)
        except Exception as exc:
            log.error("Error fetching %s: %s (attempt %d/%d)", url, exc, attempt, retries)

        if attempt < retries:
            await asyncio.sleep(1.5 * attempt)

    log.error("❌ Giving up on %s after %d attempts.", url, retries)
    return None


# ─────────────────────────────────────────
#  SCRAPER
# ─────────────────────────────────────────
async def scrape_category(session: AsyncSession, base_url: str) -> tuple[str, int]:
    """Scrape all pages in a category and save to JSON. Returns (category_name, count)."""
    category_name  = Path(urlparse(base_url).path).name
    all_items: list[dict] = []
    page = 1

    while True:
        page_url   = base_url if page == 1 else f"{base_url}?page={page}"
        html       = await fetch_page(session, page_url)
        if not html:
            break

        page_items = parse_snapshot(html)
        if not page_items:
            break

        all_items.extend(page_items)
        log.info("  %s — page %d: %d items", category_name, page, len(page_items))

        soup = BeautifulSoup(html, "html.parser")
        if not soup.find("link", rel="next"):
            break

        page += 1
        await asyncio.sleep(0.6)   # polite crawl delay

    if all_items:
        cf.save_json(all_items, DATA_DIR, prefix=category_name)

    return category_name, len(all_items)


# ─────────────────────────────────────────
#  SUMMARY TABLE
# ─────────────────────────────────────────
def show_summary_table(title: str, data_dict: dict) -> None:
    """Display a Rich summary table."""
    table = Table(title=title, show_lines=True)
    if SUPPORTS_COLOR:
        table.add_column("Category",      justify="left",  style="cyan")
        table.add_column("Items",         justify="right", style="green")
        table.add_column("Last Modified", justify="right", style="yellow")
    else:
        table.add_column("Category",      justify="left")
        table.add_column("Items",         justify="right")
        table.add_column("Last Modified", justify="right")

    for category, info in sorted(data_dict.items()):
        table.add_row(category.capitalize(), str(info["count"]), info["date"])

    console.print(table)


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
async def main() -> None:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing_categories: set[str] = set()
    for f in os.listdir(DATA_DIR):
        if f.endswith(".json") and today in f:
            cat = Path(f).stem.rsplit("_", 1)[0]
            existing_categories.add(cat)

    scraped_today: dict[str, dict] = {}

    # curl_cffi AsyncSession — impersonate="chrome" sets the TLS fingerprint,
    # HTTP/2 settings, and header order to match Chrome exactly.
    async with AsyncSession(impersonate=CHROME_IMPERSONATE) as session:

        pending_urls = [
            link for link in URLS
            if Path(urlparse(link).path).name not in existing_categories
        ]

        if pending_urls:
            console.print(f"\n🚀 Starting {len(pending_urls)} async category scrapes...\n")

            tasks   = [asyncio.create_task(scrape_category(session, link)) for link in pending_urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for link, result in zip(pending_urls, results):
                cat = Path(urlparse(link).path).name
                if isinstance(result, Exception):
                    log.error("❌ Category %s failed: %s", cat, result)
                    continue
                cat_name, count = result
                scraped_today[cat_name] = {
                    "count": count,
                    "date":  datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                }

            if scraped_today:
                show_summary_table("📦 Scraping Summary (New)", scraped_today)

        else:
            existing_data: dict[str, dict] = {}
            for f in sorted(os.listdir(DATA_DIR)):
                if not f.endswith(".json"):
                    continue
                file_path = os.path.join(DATA_DIR, f)
                try:
                    with open(file_path, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    category      = Path(f).stem.rsplit("_", 1)[0]
                    modified_time = datetime.fromtimestamp(
                        os.path.getmtime(file_path), tz=timezone.utc
                    ).strftime("%Y-%m-%d %H:%M")
                    existing_data[category] = {"count": len(data), "date": modified_time}
                except Exception as exc:
                    log.warning("Could not read %s: %s", f, exc)

            if existing_data:
                show_summary_table("📁 Existing Scraped Data", existing_data)
                console.print("✅ All categories already scraped today.\n")
            else:
                console.print("⚠️  No existing data found in directory.\n")


if __name__ == "__main__":
    asyncio.run(main())