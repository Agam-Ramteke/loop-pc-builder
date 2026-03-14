import os
from pymongo import ASCENDING, TEXT, IndexModel, MongoClient

DB_NAME = os.getenv("MONGO_DB_NAME", "PC_Parts")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
COLLECTIONS = [
    "GPUs",
    "Processors",
    "RAM",
    "Motherboards",
    "SMPS",
    "Storage",
    "Cabinets",
    "CpuCoolers",
]


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    index_models = [
        IndexModel([("price.discounted", ASCENDING)], name="price_discounted_idx"),
        IndexModel([("out_of_stock", ASCENDING)], name="out_of_stock_idx"),
        IndexModel([("image_path", ASCENDING)], name="image_path_idx"),
        IndexModel([("url", ASCENDING)], unique=True, name="url_unique_idx"),
        IndexModel([("scraped_at", ASCENDING)], name="scraped_at_idx"),
        IndexModel([("name", TEXT), ("title", TEXT)], name="name_title_text_idx"),
    ]

    for collection_name in COLLECTIONS:
        try:
            db[collection_name].create_indexes(index_models)
            print(f"Ensured indexes for {collection_name}")
        except Exception as exc:
            print(f"Failed to ensure indexes for {collection_name}: {exc}")

    client.close()


if __name__ == "__main__":
    main()
