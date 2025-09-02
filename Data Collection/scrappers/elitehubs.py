import requests
from bs4 import BeautifulSoup
import time, random

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def get_product_json(handle, use_view=True, timeout=10):
    """Fetch product JSON. If use_view True, call '?view=usf-data-json' variant."""
    if use_view:
        url = f"https://elitehubs.com/products/{handle}?view=usf-data-json"
    else:
        url = f"https://elitehubs.com/products/{handle}.json"

    try:
        res = requests.get(url, headers=HEADERS, timeout=timeout)
        res.raise_for_status()
        return res.json()
    except requests.HTTPError as e:
        print(f"HTTP error for {url}: {e} (status {getattr(e.response,'status_code',None)})")
    except requests.Timeout:
        print(f"Timeout fetching {url}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def safe_price_from_variant(variant):
    """Return price in rupees (float) if possible, otherwise None."""
    price = variant.get("price") or variant.get("price_in_paisa") or variant.get("price_cents")
    if price is None:
        return None
    # if price looks very large, assume paise and divide by 100
    price = int(price)
    if price > 100000:   # heuristic — adjust as needed
        return price / 100.0
    return price / 100.0 if price >= 100 else float(price)

# Example: get single product
if __name__ == "__main__":
    handle = "amd-ryzen-5-3500-processor"
    data = get_product_json(handle, use_view=True)
    if data:
        # some shops return {"product": {...}} and some return {...}
        product = data.get("product") if isinstance(data, dict) and "product" in data else data
        title = product.get("title")
        variants = product.get("variants", [])
        first_variant = variants[0] if variants else {}
        price = safe_price_from_variant(first_variant)
        available = first_variant.get("available")
        images = product.get("images", []) or []

        print("Title:", title)
        print("Price (INR):", price)
        print("Available:", available)
        if images:
            print("Image:", images[0])
