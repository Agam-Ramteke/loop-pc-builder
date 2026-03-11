import os
import asyncio
from pymongo import MongoClient
from rembg import remove as rembg_remove
from PIL import Image
from io import BytesIO
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger(__name__)

CONNECTION_STRING = "mongodb://localhost:27017/"
DB_NAME = "PC_Parts"

def process_image(img_path: str):
    try:
        with open(img_path, "rb") as f:
            img_bytes = f.read()
        no_bg_bytes = rembg_remove(img_bytes)
        
        # New path
        new_path = os.path.splitext(img_path)[0] + ".png"
        
        with Image.open(BytesIO(no_bg_bytes)) as img:
            img.save(new_path, format="PNG")
            
        return new_path
    except Exception as e:
        log.error("Failed to process %s: %s", img_path, e)
        return None

def main():
    client = MongoClient(CONNECTION_STRING)
    db = client[DB_NAME]
    
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        docs = list(collection.find({"image_path": {"$exists": True, "$ne": None}}))
        
        log.info("Processing %d docs in %s", len(docs), collection_name)
        
        updated = 0
        for doc in docs:
            img_path = doc["image_path"]
            
            if not os.path.exists(img_path):
                continue
                
            if img_path.lower().endswith(".png"):
                # Already processed or natively PNG. We can skip to save time,
                # assuming our new downloader saves as PNG.
                # If you want to force re-process even PNGs, comment out `continue`.
                log.debug("Skipping (already PNG): %s", img_path)
                continue
                
            log.info("Removing background from: %s", img_path)
            new_path = process_image(img_path)
            
            if new_path and new_path != img_path:
                collection.update_one({"_id": doc["_id"]}, {"$set": {"image_path": new_path}})
                updated += 1
                try:
                    os.remove(img_path)
                except OSError as e:
                    log.warning("Could not delete old image %s: %s", img_path, e)
                    
        log.info("Finished %s. Updated %d images.", collection_name, updated)

if __name__ == "__main__":
    main()
