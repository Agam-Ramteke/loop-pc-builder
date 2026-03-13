import os
import json
import asyncio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

def clean_json_files():
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    
    total_removed = 0
    for f in sorted(json_files):
        file_path = os.path.join(DATA_DIR, f)
        
        with open(file_path, "r", encoding="utf-8") as jf:
            data = json.load(jf)
            
        seen_urls = set()
        seen_names = set()
        unique_items = []
        removed = 0
        
        for item in data:
            url = item.get("url")
            name = item.get("name")
            
            if (url and url in seen_urls) or (name and name in seen_names):
                removed += 1
                continue
                
            if url: seen_urls.add(url)
            if name: seen_names.add(name)
            unique_items.append(item)
            
        if removed > 0:
            with open(file_path, "w", encoding="utf-8") as out:
                json.dump(unique_items, out, ensure_ascii=False, indent=2, default=str)
            print(f"✅ Cleaned {f}: removed {removed} duplicates. New count: {len(unique_items)}")
            total_removed += removed
        else:
            print(f"ℹ️ {f}: No duplicates.")
            
    print(f"\nTotal removed across all files: {total_removed}")

if __name__ == "__main__":
    clean_json_files()
