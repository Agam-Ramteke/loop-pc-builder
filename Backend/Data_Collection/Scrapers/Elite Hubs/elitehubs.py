import requests
from datetime import datetime
import os

def download_webpage(url: str, output_folder: str = "downloaded_pages") -> str:
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Generate a filename with timestamp so it doesn't overwrite
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"page_{timestamp}.html"
    filepath = os.path.join(output_folder, filename)

    # Add headers so the site doesn't think we're a bot from the 90s
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    try:
        print(f"Downloading: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # raises error for 4xx/5xx

        # Save HTML content
        with open(filepath, "w", encoding=response.encoding or "utf-8") as f:
            f.write(response.text)

        print(f"Saved to: {filepath}")
        return filepath

    except requests.exceptions.RequestException as e:
        print(f"Error downloading page: {e}")
        return ""

if __name__ == "__main__":
    url = "https://elitehubs.com/collections/nvidia-graphic-cards"
    download_webpage(url)
