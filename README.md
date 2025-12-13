# Loop – PC Builder (India)
Scraping-first backend plus a lightweight React dashboard to collect PC part pricing from Indian retailers.

> Status (Dec 2025): **Data collection in progress**  
> - MD Computers scraper is active (category listings → JSON → MongoDB ingest)  
> - EliteHubs processor scraper is available  
> - FastAPI job runner + minimal React UI to kick off/monitor scrapes

---

## What’s working
- **MD Computers pipeline**
  - `Bulk_data.py` grabs category listings asynchronously and saves daily JSONs in `Backend/Data_Collection/Scrapers/MD_computers/data/`.
  - `Async_Scraper.py` ingests those JSONs: downloads snapshots, parses products, downloads images with deduping, and upserts into MongoDB (per-category collections).
  - Cleans up snapshots, retries failed image downloads, and prunes/refreshes stale records.
- **EliteHubs scraper**
  - `Backend/Data_Collection/Scrapers/Elite Hubs/elitehubs.py` scrapes the processors collection, saves `processors_<date>.json`, and prunes files older than 7 days.
- **Job runner API (FastAPI)**
  - `Backend/api.py` exposes endpoints to list data files, start/stop scraper jobs (`bulk` or `async`), stream logs via WebSocket, and persist job metadata/logs.
- **Frontend dashboard (Vite + React)**
  - Located in `Frontend/`, lists data files, starts jobs through the API, shows active/past jobs, and tails logs live.

---

## Repo layout
- `Backend/` – FastAPI job runner + scraper code  
  - `Data_Collection/Scrapers/MD_computers/` – bulk + async ingest pipeline, shared utils in `common_functions.py`  
  - `Data_Collection/Scrapers/Elite Hubs/` – processor scraper  
  - `logs/`, `jobs_meta/` – persisted job output/metadata written by the API
- `Frontend/` – Vite/React dashboard that talks to the FastAPI backend
- `docs/` – architecture and scraping notes

---

## Prerequisites
- Python 3.10+ and pip
- Node.js 18+ and npm (for the dashboard)
- MongoDB reachable at `mongodb://localhost:27017/` (default used by `Async_Scraper.py`)

---

## Backend setup
```bash
cd Backend
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r ../requirements.txt

# Start API (serves scraper runner + logs)
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```
Optional auth: set `API_KEY=<token>` (FastAPI will expect `X-API-Key`).

---

## Frontend setup
```bash
cd Frontend
npm install
npm run dev
```
Configure API target via `.env` (optional):
```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_KEY=<token-if-set>
```

---

## Running scrapers directly (without the API)
MD Computers (category listings):
```bash
cd Backend/Data_Collection/Scrapers/MD_computers
python Bulk_data.py --all                  # scrape all categories
# python Bulk_data.py --categories processor,ram --page-limit 2
```

MD Computers (detail ingest → MongoDB):
```bash
cd Backend/Data_Collection/Scrapers/MD_computers
python Async_Scraper.py --all              # process all JSONs in data/
# python Async_Scraper.py --file processor_2025-12-09.json --limit 20
# python Async_Scraper.py --all --dry      # parse only, no DB writes
```

EliteHubs processors:
```bash
cd "Backend/Data_Collection/Scrapers/Elite Hubs"
python Bulk_data.py
```

---

## API quick reference
- `GET /files` – list available JSON files in `MD_computers/data`
- `POST /jobs/start` – body `{ "script": "bulk"|"async", ... }` mirrors CLI flags (see `Backend/api.py`)
- `GET /jobs` / `GET /jobs/{id}` – inspect running jobs
- `GET /jobs/{id}/logs` – persisted log tail; live logs stream over `ws://.../ws/jobs/{id}`
- `POST /jobs/{id}/stop` – terminate a running scraper

---

## Notes
- Daily JSON outputs (e.g., `processor_2025-12-09.json`) live in `Backend/Data_Collection/Scrapers/MD_computers/data/`.
- Product images are saved under `Backend/Data_Collection/Scrapers/MD_computers/product_images/`.
- Job logs are written to `Backend/logs/`, metadata to `Backend/jobs_meta/`.
- For scraper implementation details, see `docs/scraping_notes.md`.
