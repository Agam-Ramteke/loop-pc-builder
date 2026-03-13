"""
Quick one-off script to backfill PrimeABGB listing prices into MongoDB.

Reads the bulk JSON data files and updates any documents that currently
have no price data (price.discounted is null/empty).

Usage:
    python backfill_prices.py          # dry-run (preview only)
    python backfill_prices.py --apply  # actually update MongoDB
"""
import os
import glob
import json
import sys
from pymongo import MongoClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DB_NAME = "PC_Parts"
CONNECTION_STRING = "mongodb://localhost:27017/"

COLLECTION_MAP = {
    "processor":     "Processors",
    "graphics-card": "GPUs",
    "ram":           "RAM",
    "ssd":           "Storage",
    "hdd":           "Storage",
    "motherboard":   "Motherboards",
    "smps":          "SMPS",
    "cabinet":       "Cabinets",
    "cpu-cooler":    "CpuCoolers",
}


def main():
    apply = "--apply" in sys.argv

    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]

    total_updated = 0
    total_skipped = 0
    total_not_found = 0

    for slug, coll_name in COLLECTION_MAP.items():
        json_files = glob.glob(os.path.join(DATA_DIR, f"{slug}_*.json"))
        if not json_files:
            print(f"  [{slug}] No JSON files found, skipping")
            continue

        # Use the most recent file
        json_files.sort(key=os.path.getmtime, reverse=True)
        with open(json_files[0], "r", encoding="utf-8") as f:
            products = json.load(f)

        collection = db[coll_name]
        updated = 0
        skipped = 0
        not_found = 0

        for product in products:
            url = product.get("url")
            price = product.get("price", {})
            if not url or not isinstance(price, dict):
                continue

            # Check if this document exists and already has a price
            existing = collection.find_one({"url": url}, {"price": 1})
            if not existing:
                not_found += 1
                continue

            existing_price = existing.get("price", {})
            if isinstance(existing_price, dict) and existing_price.get("discounted"):
                skipped += 1
                continue

            # This product has no price in the DB — update it
            update_fields = {}
            if price.get("discounted"):
                update_fields["price.discounted"] = price["discounted"]
            if price.get("original"):
                update_fields["price.original"] = price["original"]
            if price.get("discount"):
                update_fields["price.discount"] = price["discount"]

            if not update_fields:
                skipped += 1
                continue

            if apply:
                collection.update_one({"url": url}, {"$set": update_fields})

            updated += 1

        print(f"  [{slug:15s} → {coll_name:12s}] "
              f"updated={updated}, already_has_price={skipped}, not_in_db={not_found}")
        total_updated += updated
        total_skipped += skipped
        total_not_found += not_found

    print(f"\n{'=' * 60}")
    print(f"  Total: updated={total_updated}, already_has_price={total_skipped}, not_in_db={total_not_found}")

    if not apply:
        print(f"\n  ⚠️  DRY RUN — no changes were made.")
        print(f"  Run with --apply to actually update MongoDB.")
    else:
        print(f"\n  ✅ Done! {total_updated} documents updated in MongoDB.")

    client.close()


if __name__ == "__main__":
    main()
