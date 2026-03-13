"""
Temporary script: Back-fill missing price.discounted values in MongoDB
from the Bulk_data.py JSON files, and auto-calculate price.discount where missing.

Usage:
    python fix_prices_in_db.py            # dry-run (preview changes)
    python fix_prices_in_db.py --apply    # actually write to DB
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import re
import json
import glob
import argparse
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

CONNECTION_STRING = "mongodb://localhost:27017/"
DB_NAME = "PC_Parts"

COLLECTION_MAP = {
    "graphics-card": "GPUs",
    "processor":     "Processors",
    "ram":           "RAM",
    "motherboard":   "Motherboards",
    "smps":          "SMPS",
    "storage":       "Storage",
    "cabinet":       "Cabinets",
    "cpu-cooler":    "CpuCoolers",
}


def parse_price(price_str: str | None) -> float | None:
    """Extract numeric price from a string like '₹12,345'."""
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


def calc_discount(original_str: str | None, discounted_str: str | None) -> str | None:
    """Calculate discount percentage string like '-30%'."""
    orig = parse_price(original_str)
    disc = parse_price(discounted_str)
    if orig and disc and orig > disc:
        pct = round((1 - disc / orig) * 100)
        if pct > 0:
            return f"-{pct}%"
    return None


def fix_from_json_files(db, apply: bool) -> dict:
    """Back-fill prices from local JSON files into MongoDB."""
    stats = {"checked": 0, "updated_from_json": 0, "discount_calculated": 0, "skipped": 0}

    json_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    if not json_files:
        print(f"  No JSON files found in {DATA_DIR}")
        return stats

    for file_path in json_files:
        base_name = os.path.basename(file_path).rsplit("_", 1)[0].lower()
        coll_name = COLLECTION_MAP.get(base_name)
        if not coll_name:
            print(f"  ⚠ Skipping unknown category file: {os.path.basename(file_path)}")
            continue

        collection = db[coll_name]

        with open(file_path, "r", encoding="utf-8") as f:
            items = json.load(f)

        print(f"\n  📂 {os.path.basename(file_path)} → {coll_name} ({len(items)} items)")

        for item in items:
            url = item.get("url")
            if not url:
                continue

            stats["checked"] += 1
            json_price = item.get("price", {})
            json_original = json_price.get("original")
            json_discounted = json_price.get("discounted")

            if not json_original and not json_discounted:
                stats["skipped"] += 1
                continue

            # Find the DB document
            doc = collection.find_one({"url": url}, {"price": 1, "name": 1})
            if not doc:
                stats["skipped"] += 1
                continue

            db_price = doc.get("price", {}) if isinstance(doc.get("price"), dict) else {}
            updates = {}

            # Back-fill discounted price if missing in DB but present in JSON
            if not db_price.get("discounted") and json_discounted:
                updates["price.discounted"] = json_discounted

            # Back-fill original price if missing in DB but present in JSON
            if not db_price.get("original") and json_original:
                updates["price.original"] = json_original

            # Compute effective prices for discount calculation
            effective_original = db_price.get("original") or json_original
            effective_discounted = updates.get("price.discounted") or db_price.get("discounted") or json_discounted

            # Auto-calculate discount if missing
            if not db_price.get("discount") and effective_original and effective_discounted:
                discount = calc_discount(effective_original, effective_discounted)
                if discount:
                    updates["price.discount"] = discount
                    stats["discount_calculated"] += 1

            if updates:
                name = (doc.get("name") or url or "unknown")[:60]
                print(f"    {'✅' if apply else '🔍'} {name}")
                for key, val in updates.items():
                    print(f"       {key}: {val}")

                if apply:
                    collection.update_one({"_id": doc["_id"]}, {"$set": updates})

                stats["updated_from_json"] += 1

    return stats


def fix_discount_only(db, apply: bool) -> dict:
    """For docs that already have original + discounted but no discount %, calculate it."""
    stats = {"checked": 0, "discount_calculated": 0}

    for coll_name in COLLECTION_MAP.values():
        collection = db[coll_name]

        # Find docs with both prices but no discount
        cursor = collection.find({
            "price.original": {"$exists": True, "$nin": [None, ""]},
            "price.discounted": {"$exists": True, "$nin": [None, ""]},
            "$or": [
                {"price.discount": {"$exists": False}},
                {"price.discount": None},
                {"price.discount": ""},
            ]
        }, {"price": 1, "name": 1})

        for doc in cursor:
            stats["checked"] += 1
            price = doc.get("price", {})
            discount = calc_discount(price.get("original"), price.get("discounted"))
            if discount:
                name = (doc.get("name") or "Unknown")[:60]
                print(f"    {'✅' if apply else '🔍'} {name} → {discount}")
                if apply:
                    collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"price.discount": discount}}
                    )
                stats["discount_calculated"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Fix missing price data in MongoDB")
    parser.add_argument("--apply", action="store_true", help="Actually write changes (default is dry-run)")
    args = parser.parse_args()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"\n{'='*60}")
    print(f"  Price Fix Script — {mode} MODE")
    print(f"{'='*60}")

    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    print(f"\n📦 Step 1: Back-fill prices from JSON files...")
    json_stats = fix_from_json_files(db, apply=args.apply)

    print(f"\n📊 Step 2: Calculate missing discount percentages...")
    disc_stats = fix_discount_only(db, apply=args.apply)

    print(f"\n{'='*60}")
    print(f"  SUMMARY ({mode})")
    print(f"{'='*60}")
    print(f"  JSON back-fill:")
    print(f"    Checked:         {json_stats['checked']}")
    print(f"    Updated:         {json_stats['updated_from_json']}")
    print(f"    Discounts added: {json_stats['discount_calculated']}")
    print(f"    Skipped:         {json_stats['skipped']}")
    print(f"  Discount calc pass:")
    print(f"    Checked:         {disc_stats['checked']}")
    print(f"    Discounts added: {disc_stats['discount_calculated']}")
    print()

    if not args.apply:
        print("  ℹ️  This was a DRY-RUN. No changes were written.")
        print("  ℹ️  Run with --apply to actually update the database.\n")

    client.close()


if __name__ == "__main__":
    main()
