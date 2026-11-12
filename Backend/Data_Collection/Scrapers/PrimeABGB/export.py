import os
import json
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

# --- CONFIGURATION ---
DB_NAME = os.getenv("MONGO_DB_NAME", "PC_Parts")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
EXPORT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exports")

# List of collections to export (from ensure_mongo_indexes.py)
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

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, ObjectId)):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def export_collections():
    """Connects to MongoDB and exports specified collections to JSON files."""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        print(f"Created export directory: {EXPORT_DIR}")

    client = None
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        # Verify connection
        client.admin.command('ping')
        print(f"Connected to MongoDB at {MONGO_URI}")

        for coll_name in COLLECTIONS:
            print(f"Exporting collection: {coll_name}...")
            collection = db[coll_name]
            
            # Fetch all documents
            documents = list(collection.find({}))
            
            if not documents:
                print(f"  Empty collection. Skipping.")
                continue

            # Define export path
            file_name = f"{coll_name.lower()}.json"
            file_path = os.path.join(EXPORT_DIR, file_name)
            
            # Save as JSON
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(documents, f, default=json_serial, indent=4)
            
            print(f"  Successfully exported {len(documents)} documents to {file_path}")

    except Exception as e:
        print(f"An error occurred during export: {e}")
    finally:
        if client:
            client.close()
            print("MongoDB connection closed.")

if __name__ == "__main__":
    export_collections()
