import os
import json
import requests
import hashlib
import threading
import queue
import random
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Set, Dict, Any
from pymongo import MongoClient
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from curl_cffi.requests import AsyncSession as CurlSession
import curl_cffi.requests as curl_sync
import aiohttp
import asyncio
from urllib.parse import urljoin, urlparse
from bson import ObjectId

# curl_cffi replicates Chrome's exact TLS fingerprint (JA3 + ALPN + cipher order)
# so Cloudflare/WAF bot filters cannot distinguish it from a real browser.
# mdcomputers.in serves images from the same domain — TLS fingerprinting applies
# to image requests too, so curl_cffi is used for ALL downloads.
# Type alias covering both session types so call-sites don't need to care
_AnySession = CurlSession | aiohttp.ClientSession

log = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────
DEFAULT_USER_AGENT  = "Mozilla/5.0 (compatible; Scraper/1.0)"
MAX_FILENAME_LENGTH = 150
MAX_HTML_SIZE       = 2_000_000   # 2 MB — truncate HTML if larger
DEFAULT_ASYNC_TIMEOUT = 30        # seconds

# FIX: DEBUG defined once at module level (was defined twice, once before each async function)
DEBUG = True

# FIX: UserAgent instantiated once — init downloads a JSON DB, doing it per-call is very slow
try:
    _ua = UserAgent()
    def _random_ua() -> str:
        return _ua.random
except Exception:
    def _random_ua() -> str:   # type: ignore[misc]
        return DEFAULT_USER_AGENT


# ─────────────────────────────────────────
#  UTILITIES
# ─────────────────────────────────────────
def safe_filename(name: str) -> str:
    """Sanitize string into a valid filename (Windows-safe, length-capped)."""
    if not name:
        return ""
    s = name.replace("https://", "").replace("http://", "")
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", "_", s)
    return s[:MAX_FILENAME_LENGTH]


def slugify(url: str) -> str:
    """Compat wrapper — delegates to safe_filename."""
    return safe_filename(url)


def content_hash(content: bytes | str) -> str:
    """MD5 hash for deduplication (not for security)."""
    h = hashlib.md5()
    if isinstance(content, str):
        content = content.encode("utf-8")
    h.update(content)
    return h.hexdigest()


# ─────────────────────────────────────────
#  JSON / FILE HELPERS
# ─────────────────────────────────────────
def save_json(data: Any, folder: str, prefix: str = "data") -> str:
    """
    Save data to a timestamped JSON file.
    Cleans up files with the same prefix that are older than 2 days.
    Returns the saved filepath.
    """
    os.makedirs(folder, exist_ok=True)
    today = datetime.now(timezone.utc).date()

    for filename in os.listdir(folder):
        if filename.endswith(".json") and filename.startswith(prefix):
            try:
                date_str  = filename.rsplit("_", 1)[-1].replace(".json", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if (today - file_date).days > 2:
                    try:
                        os.remove(os.path.join(folder, filename))
                        log.info("🗑️  Deleted old file: %s", filename)
                    except OSError as exc:
                        log.warning("Could not delete %s: %s", filename, exc)
            except Exception:
                pass

    timestamp = today.strftime("%Y-%m-%d")
    filename  = f"{prefix}_{timestamp}.json"
    filepath  = os.path.join(folder, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return filepath


# ─────────────────────────────────────────
#  SNAPSHOT DOWNLOADERS
# ─────────────────────────────────────────
def save_snapshot(
    url: str,
    folder: str,
    prefix: str = "",
    page: Optional[int] = None,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
    max_size: int = MAX_HTML_SIZE,
) -> Optional[str]:
    """Synchronous snapshot saver (requests). Returns filepath or None."""
    os.makedirs(folder, exist_ok=True)
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra    = f"_p{page}" if page else ""
    slug     = safe_filename(url)
    filepath = os.path.join(folder, f"{prefix}_{today}{extra}_{slug}.html")

    try:
        resp = requests.get(
            url,
            # FIX: use module-level UA singleton instead of constructing per call
            headers={"User-Agent": _random_ua()},
            timeout=timeout,
        )
        resp.raise_for_status()
        text = resp.text
        if max_size and len(text) > max_size:
            text = text[:max_size]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        return filepath
    except Exception as exc:
        log.warning("⚠️  save_snapshot failed for %s: %s", url, exc)
        return None


async def async_save_snapshot(
    session: CurlSession,
    url: str,
    folder: str,
    prefix: str = "",
    page: Optional[int] = None,
    timeout: int = DEFAULT_ASYNC_TIMEOUT,
    max_size: int = MAX_HTML_SIZE,
) -> Optional[str]:
    """
    Async snapshot saver using curl_cffi (Chrome TLS impersonation).
    curl_cffi's .get() returns the response directly (not a context manager),
    and .text is a plain property — not a coroutine.
    Returns filepath or None.
    """
    os.makedirs(folder, exist_ok=True)
    today    = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    extra    = f"_p{page}" if page else ""
    slug     = safe_filename(url)
    filepath = os.path.join(folder, f"{prefix}_{today}{extra}_{slug}.html")

    try:
        resp = await session.get(url, timeout=timeout)
        resp.raise_for_status()
        text = resp.text   # property, not coroutine
        if max_size and len(text) > max_size:
            text = text[:max_size]
        await asyncio.to_thread(_write_text_file, filepath, text)
        return filepath

    except Exception as exc:
        log.warning("⚠️  async_save_snapshot failed for %s: %s", url, exc)
        return None


async def download_with_retry(
    session: CurlSession,
    url: str,
    folder: str,
    prefix: str,
    retries: int = 3,
    backoff: tuple = (1.0, 3.0),
    page: Optional[int] = None,
) -> Optional[str]:
    """Retry wrapper around async_save_snapshot."""
    for attempt in range(1, retries + 1):
        snap = await async_save_snapshot(session, url, folder, prefix, page=page)
        if snap:
            return snap
        if attempt < retries:
            wait = random.uniform(*backoff)
            log.warning("⚠️  Retry %d/%d for %s (waiting %.1fs)", attempt, retries, url, wait)
            await asyncio.sleep(wait)

    log.error("❌ Giving up on %s after %d attempts.", url, retries)
    return None


# ─────────────────────────────────────────
#  IMAGE HELPERS
# ─────────────────────────────────────────
def extract_image_url_from_soup(
    soup: BeautifulSoup, base_url: Optional[str] = None
) -> Optional[str]:
    """
    Multi-strategy image URL extractor from a product page soup.
    Priority: OG tag → JSON-LD → lazy-load attrs → srcset → src.
    """
    # 1) Open Graph
    og = soup.select_one('meta[property="og:image"], meta[name="og:image"]')
    if og and og.get("content"):
        return urljoin(base_url or "", og["content"].strip())

    # 2) JSON-LD schema.org
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            j = json.loads(script.string or "{}")
            entries = j if isinstance(j, list) else [j]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                img = entry.get("image") or (entry.get("mainEntityOfPage") or {}).get("image")
                if isinstance(img, str):
                    return urljoin(base_url or "", img)
                if isinstance(img, list) and img:
                    return urljoin(base_url or "", img[0])
        except Exception:
            continue

    # 3) Common lazy-load attributes
    for attr in ("data-src", "data-lazy-src", "data-cfsrc", "src"):
        tag = soup.select_one(f"img[{attr}]")
        if tag and tag.get(attr):
            return urljoin(base_url or "", tag[attr].strip())

    # 4) srcset fallback
    tag = soup.select_one("img[srcset], img")
    if tag:
        srcset = tag.get("srcset", "")
        if srcset:
            first = srcset.split(",")[0].strip().split(" ")[0]
            if first:
                return urljoin(base_url or "", first)
        if tag.get("src"):
            return urljoin(base_url or "", tag["src"])

    return None


def download_image(
    image_url: str,
    product_url: str,
    folder: str,
    collection=None,
    db_filter: Optional[dict] = None,
    seen_hashes: Optional[Set[str]] = None,
    timeout: int = 20,
) -> Optional[str]:
    """
    Synchronous image downloader.
    Checks DB and filesystem before downloading to avoid redundant work.
    """
    if not image_url:
        return None
    if seen_hashes is None:
        seen_hashes = set()

    os.makedirs(folder, exist_ok=True)
    slug     = safe_filename(product_url)
    ext      = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    # Fast-path: file already on disk
    if os.path.exists(filepath):
        return filepath

    # FIX: check DB BEFORE downloading (was checked after — wasted bandwidth)
    if collection is not None and db_filter:
        existing = collection.find_one(db_filter)
        if existing and existing.get("image_path") and os.path.exists(existing["image_path"]):
            return existing["image_path"]

    try:
        norm = image_url if image_url.startswith("http") else "https://" + image_url.lstrip("//")
        resp = curl_sync.get(
            norm,
            headers={"User-Agent": _random_ua()},
            timeout=timeout,
            impersonate="chrome",
        )
        resp.raise_for_status()
        img_bytes = resp.content

        img_hash = content_hash(img_bytes)
        if img_hash in seen_hashes:
            return filepath
        seen_hashes.add(img_hash)

        with open(filepath, "wb") as f:
            f.write(img_bytes)
        return filepath

    except Exception as exc:
        log.warning("⚠️  download_image failed for %s: %s", image_url, exc)
        return None


async def async_download_image(
    session: CurlSession,
    image_url: str,
    product_url: str,
    folder: str,
    collection=None,
    db_filter: Optional[dict] = None,
    seen_hashes: Optional[Set[str]] = None,
    timeout: int = DEFAULT_ASYNC_TIMEOUT,
) -> Optional[str]:
    """
    Async image downloader using curl_cffi (Chrome TLS impersonation).
    mdcomputers.in serves images from the same domain, so TLS fingerprinting
    applies — aiohttp gets 403 Forbidden.
    Deduplicates via content hash and DB lookup.
    """
    if not image_url:
        return None
    if seen_hashes is None:
        seen_hashes = set()

    os.makedirs(folder, exist_ok=True)
    slug     = safe_filename(product_url)
    ext      = os.path.splitext(image_url.split("?")[0])[1] or ".jpg"
    filepath = os.path.join(folder, f"{slug}{ext}")

    if os.path.exists(filepath):
        return filepath

    if collection is not None and db_filter:
        existing = collection.find_one(db_filter)
        if existing and existing.get("image_path") and os.path.exists(existing["image_path"]):
            return existing["image_path"]

    try:
        norm = image_url if image_url.startswith("http") else "https://" + image_url.lstrip("//")
        resp = await session.get(norm, timeout=timeout)
        resp.raise_for_status()
        img_bytes = resp.content

        img_hash = content_hash(img_bytes)
        if img_hash in seen_hashes:
            return filepath
        seen_hashes.add(img_hash)

        await asyncio.to_thread(_write_binary_file, filepath, img_bytes)
        return filepath

    except Exception as exc:
        log.warning("⚠️  async_download_image failed for %s: %s", image_url, exc)
        return None


# ─────────────────────────────────────────
#  INTERNAL FILE WRITERS (thread-safe helpers)
# ─────────────────────────────────────────
def _write_binary_file(path: str, data: bytes) -> None:
    """Write binary data to disk. Safe to call via asyncio.to_thread."""
    parent = os.path.dirname(path)
    # FIX: only call makedirs if there is actually a parent directory to create
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def _write_text_file(path: str, text: str) -> None:
    """Write text data to disk. Safe to call via asyncio.to_thread."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# ─────────────────────────────────────────
#  MONGODB HELPERS
# ─────────────────────────────────────────
def upsert_product(
    data: dict,
    db_or_conn,
    db_name: Optional[str] = None,
    collection_name: Optional[str] = None,
    unique_keys: tuple = ("url",),
    verbose: bool = False,
) -> str:
    """
    Upsert a product document. Accepts a MongoClient or a connection string.
    Always closes a connection-string-based client after use.
    """
    if not collection_name:
        raise ValueError("collection_name is required")

    # FIX: track whether we own the client so we can close it
    _owned_client = None
    if isinstance(db_or_conn, MongoClient):
        db = db_or_conn[db_name]
    else:
        # FIX: was leaking MongoClient when a connection string was passed
        _owned_client = MongoClient(db_or_conn)
        db = _owned_client[db_name]

    try:
        collection = db[collection_name]
        query = {k: data[k] for k in unique_keys if k in data}
        if not query:
            raise ValueError(f"None of {unique_keys} found in data")

        result = collection.update_one(query, {"$set": data}, upsert=True)
        action = "🔁 Updated" if result.matched_count else "🆕 Inserted"
        if verbose:
            log.info("%s %s", action, data.get("name", "<unknown>"))
        return "updated" if result.matched_count else "inserted"
    finally:
        if _owned_client is not None:
            _owned_client.close()


# ─────────────────────────────────────────
#  CLEANUP HELPERS
# ─────────────────────────────────────────
async def async_remove_non_internal_storage(
    conn_string: str, db_name: str, image_dir: str = "product_images"
) -> None:
    """
    Remove storage entries that are not flagged as 'internal' in their specs,
    and delete their associated images.
    """
    # FIX: client explicitly closed in finally block
    client = MongoClient(conn_string)
    try:
        db         = client[db_name]
        collection = db["Storage"]

        log.info("🔍 Starting async cleanup for non-internal storage drives...")

        items = await asyncio.to_thread(
            lambda: list(collection.find({}, {"specifications": 1, "name": 1, "url": 1, "image_path": 1}))
        )

        # FIX: asyncio.Lock guards `removed` counter — nonlocal int + concurrent coroutines = race
        lock    = asyncio.Lock()
        removed = 0

        async def check_and_remove(item: dict) -> None:
            nonlocal removed
            try:
                specs      = item.get("specifications") or {}
                specs_text = " ".join(f"{k} {v}".lower() for k, v in specs.items())

                if "internal" not in specs_text:
                    await asyncio.to_thread(collection.delete_one, {"url": item["url"]})
                    async with lock:
                        removed += 1
                    log.info("🗑️  Removed non-internal storage: %s", item.get("name"))

                    image_path = item.get("image_path")
                    if image_path and os.path.exists(image_path):
                        try:
                            await asyncio.to_thread(os.remove, image_path)
                            if DEBUG:
                                log.debug("🧹 Deleted image: %s", image_path)
                        except OSError as exc:
                            log.warning("⚠️  Failed to delete image %s: %s", image_path, exc)

            except Exception as exc:
                log.warning("⚠️  Error processing %s: %s", item.get("name", "Unknown"), exc)

        await asyncio.gather(*[check_and_remove(item) for item in items])
        log.info("✅ Storage cleanup complete — removed %d non-internal drives.\n", removed)

    finally:
        client.close()


# ─────────────────────────────────────────
#  INPUT WITH TIMEOUT
# ─────────────────────────────────────────
def input_with_timeout(prompt: str, timeout: int = 10) -> str:
    """Prompt for input; returns empty string if user doesn't respond in time."""
    print(f"{prompt} (auto-selects ALL after {timeout}s): ", end="", flush=True)
    q: queue.Queue = queue.Queue()

    def _read() -> None:
        try:
            q.put(input())
        except Exception:
            q.put("")

    threading.Thread(target=_read, daemon=True).start()
    try:
        return q.get(timeout=timeout)
    except queue.Empty:
        print("\nAuto-selecting ALL.")
        return ""


# ─────────────────────────────────────────
#  HTML PARSING
# ─────────────────────────────────────────
def _parse_price_number(price_str: Optional[str]) -> Optional[float]:
    """Extract a numeric price from a string like '₹12,345'."""
    if not price_str:
        return None
    import re as _re
    match = _re.findall(r"[\d,.]+", price_str)
    if not match:
        return None
    cleaned = "".join(match).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _calculate_discount_percent(
    original_str: Optional[str], discounted_str: Optional[str]
) -> Optional[str]:
    """Auto-calculate discount % when both original and discounted prices are available."""
    orig = _parse_price_number(original_str)
    disc = _parse_price_number(discounted_str)
    if orig and disc and orig > disc:
        pct = round((1 - disc / orig) * 100)
        if pct > 0:
            return f"-{pct}%"
    return None


def parse_product_page(
    html_file_path: str,
    product_url: Optional[str] = None,
    image_url: Optional[str] = None,
    collection=None,
    image_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse product details from a saved HTML snapshot.
    Returns a dict ready for upsert_product.

    FIX: When the product-page parser cannot find prices (selectors don't
    match), it now falls back to any existing price data already stored
    in the DB (populated earlier by Bulk_data.py from category pages).
    This prevents valid prices from being overwritten with nulls.
    """
    with open(html_file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    # Name
    name_el = soup.select_one("h1.product-name-title")
    name    = name_el.get_text(strip=True) if name_el else None

    # Prices — try multiple selector strategies
    price_new   = soup.select_one("span.price-new")
    price_old   = soup.select_one("span.price-old")
    discount_el = soup.select_one(".discount-percentage")

    parsed_prices = {
        "discounted": price_new.get_text(strip=True)   if price_new   else None,
        "original":   price_old.get_text(strip=True)   if price_old   else None,
        "discount":   discount_el.get_text(strip=True) if discount_el else None,
    }

    # FIX: If product-page selectors found nothing, fall back to existing
    # DB data (which Bulk_data.py already populated from category listings).
    existing_price: Dict[str, Any] = {}
    if collection is not None and product_url:
        existing_doc = collection.find_one({"url": product_url}, {"price": 1})
        if existing_doc and isinstance(existing_doc.get("price"), dict):
            existing_price = existing_doc["price"]

    prices = {
        "discounted": parsed_prices["discounted"] or existing_price.get("discounted"),
        "original":   parsed_prices["original"]   or existing_price.get("original"),
        "discount":   parsed_prices["discount"]   or existing_price.get("discount"),
    }

    # Auto-calculate discount % when we have both prices but no explicit discount
    if not prices["discount"] and prices["original"] and prices["discounted"]:
        prices["discount"] = _calculate_discount_percent(
            prices["original"], prices["discounted"]
        )

    # Stock
    stock_el     = soup.select_one("span.base-color.ms-auto")
    stock_status = stock_el.get_text(strip=True) if stock_el else None

    # Specifications
    specifications: Dict[str, str] = {}
    for row in soup.select("div#tab-specification table.table tr"):
        cols = row.find_all("td")
        if len(cols) == 2:
            specifications[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

    # Image
    # FIX: save to product_images dir (caller-supplied or sibling of snapshot dir),
    #      NOT to snapshots/images which gets wiped on cleanup
    local_image_path = None
    try:
        resolved_image_url = image_url
        if not resolved_image_url:
            resolved_image_url = extract_image_url_from_soup(soup, base_url=product_url)

        if image_dir is None:
            # Default: product_images/ next to the snapshot directory
            image_dir = os.path.join(os.path.dirname(os.path.dirname(html_file_path)), "product_images")

        local_image_path = download_image(
            resolved_image_url,
            product_url=product_url,
            folder=image_dir,
            collection=collection,
            db_filter={"url": product_url} if product_url else None,
        )
    except Exception as exc:
        log.warning("Image download failed for %s: %s", product_url, exc)
        local_image_path = None

    return {
        "name":           name,
        "url":            product_url,
        "image_path":     local_image_path,
        "price":          prices,
        "stock_status":   stock_status,
        "specifications": specifications,
        "source":         "MD Computers",
        "scraped_at":     datetime.now(timezone.utc),
    }


# ─────────────────────────────────────────
#  IMAGE RECOVERY
# ─────────────────────────────────────────
async def async_recover_missing_images(
    conn_string: str,
    db_name: str,
    image_dir: str = "product_images",
    concurrency: int = 15,
) -> None:
    """
    Scan all collections for documents whose image file is missing.
    Re-download and update the DB record if recoverable.
    """
    # FIX: client explicitly closed in finally block
    client = MongoClient(conn_string)
    try:
        db         = client[db_name]
        semaphore  = asyncio.Semaphore(concurrency)
        # FIX: asyncio.Lock for concurrent counter mutations
        lock           = asyncio.Lock()
        total_missing  = 0
        total_fixed    = 0

        log.info("🔍 Starting async image recovery check...")
        collection_names = db.list_collection_names()

        async with CurlSession(impersonate="chrome") as page_session:

            async def check_and_fix_image(col_name: str, doc: dict) -> None:
                nonlocal total_missing, total_fixed
                async with semaphore:
                    try:
                        img_url    = doc.get("image_url")
                        img_path   = doc.get("image_path")
                        name       = doc.get("name", "Unknown")
                        url        = doc.get("url")

                        if img_path and os.path.exists(img_path):
                            return   # image is present — nothing to do

                        async with lock:
                            total_missing += 1

                        # If no image_url, fetch the product page (needs TLS impersonation)
                        if not img_url and url:
                            if DEBUG:
                                log.debug("🔎 No image_url for %s — fetching product page", name)
                            try:
                                resp = await page_session.get(
                                    url,
                                    headers={"User-Agent": _random_ua()},
                                    timeout=20,
                                )
                                resp.raise_for_status()
                                page_soup = BeautifulSoup(resp.text, "html.parser")
                                img_url   = extract_image_url_from_soup(page_soup, base_url=url)
                                if img_url and DEBUG:
                                    log.debug("🔗 Extracted image_url: %s", img_url)
                            except Exception as exc:
                                log.warning("⚠️  Failed to fetch product page for %s: %s", name, exc)

                        if not img_url:
                            if DEBUG:
                                log.warning("⚠️  No image URL available for %s", name)
                            return

                        # Build target filename
                        parsed    = urlparse(url or "")
                        base      = parsed.path.replace("/", "_").strip("_") or safe_filename(name or str(doc.get("_id")))
                        ext       = os.path.splitext(img_url.split("?")[0])[1]
                        safe_base = safe_filename(base)
                        new_path  = os.path.join(image_dir, f"{safe_base}{ext}")
                        os.makedirs(image_dir, exist_ok=True)

                        # Download image via curl_cffi — same domain needs TLS impersonation
                        norm = img_url if img_url.startswith("http") else "https://" + img_url.lstrip("//")
                        try:
                            resp = await page_session.get(
                                norm,
                                headers={"User-Agent": _random_ua()},
                                timeout=30,
                            )
                            resp.raise_for_status()
                            content = resp.content
                            if not ext:
                                ct = resp.headers.get("content-type", "")
                                if "/" in ct:
                                    guessed = ct.split("/")[-1].split(";")[0]
                                    if guessed not in ("plain", "html"):
                                        new_path = os.path.join(image_dir, f"{safe_base}.{guessed}")

                            await asyncio.to_thread(_write_binary_file, new_path, content)
                            await asyncio.to_thread(
                                db[col_name].update_one,
                                {"_id": doc["_id"]},
                                {"$set": {"image_path": new_path, "image_url": img_url}},
                            )
                            async with lock:
                                total_fixed += 1
                            if DEBUG:
                                log.debug("🧩 Recovered image for %s → %s", name, new_path)

                        except Exception as exc:
                            log.error("❌ Failed to redownload image for %s: %s", name, exc)

                    except Exception as exc:
                        log.warning("⚠️  Error processing doc in %s: %s", col_name, exc)

            for col_name in collection_names:
                # FIX: lambda closure bug — `collection` changed each iteration.
                # Capture current value with a default argument.
                col  = db[col_name]
                docs = await asyncio.to_thread(
                    lambda c=col: list(
                        c.find({}, {"_id": 1, "url": 1, "image_url": 1, "image_path": 1, "name": 1})
                    )
                )
                log.info("📂 Checking %s (%d docs)", col_name, len(docs))
                await asyncio.gather(*[check_and_fix_image(col_name, doc) for doc in docs])

        log.info("✅ Image recovery complete. Missing: %d | Recovered: %d", total_missing, total_fixed)

    finally:
        client.close()
