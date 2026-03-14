# Loop – Premium PC Part Tracker (India)

**Loop** is a high-performance PC component pricing aggregator designed for the Indian market. It combines a fleet of asynchronous Python scrapers with a cutting-edge Next.js 16 frontend to provide a seamless browsing experience with real-time (cached) pricing from top retailers.

> **Status (March 2026):** Completely migrated to Next.js 16 (Turbopack) with a centralized API layer and integrated Redis caching. Scraper support includes MD Computers, EliteHubs, and PrimeABGB.

---

## ⚡ Core Features

- **Multi-Retailer Scraping Engine**
  - **MD Computers**: Full category coverage with async ingest pipeline.
  - **EliteHubs**: Processor-specific scrapers with automated pruning.
  - **PrimeABGB**: Recent integration focusing on precise specification extraction.
- **Premium User Interface**
  - **Antigravity Design**: Physics-based canvas starfield, interactive cursor particles, and sleek glassmorphism.
  - **Performance Optimized**: Uses CSS blend modes for product images to avoid expensive background removal logic while maintaining a clean look.
  - **Dynamic Architecture**: Built on **Next.js 16 (App Router)** and **React 19**.
- **Robust API & Caching**
  - Unified data API at `/api/components` using MongoDB aggregations.
  - **Redis Integration**: High-speed caching layer to ensure sub-millisecond response times for frequent queries.

---

## 🏗️ Project Structure

```text
├── Backend/                 # Python Data Ingestion Layer
│   └── Data_Collection/     # Retailer-specific scrapers
│       ├── MD_computers/    # Bulk + Async ingest pipeline
│       ├── Elite Hubs/      # Processor scrapers
│       └── PrimeABGB/       # Recent specialized scraper
├── Frontend/                # Next.js 16 Web Application
│   ├── src/app/api/         # Unified API routes (Next.js)
│   ├── src/lib/             # Shared logic (Redis, MongoDB, UI components)
│   └── public/              # Static assets
└── docker-compose.yml       # Full stack infrastructure (Mongo + Redis)
```

---

## 🚀 Getting Started

### 1. Infrastructure (Docker)
The easiest way to get the database and cache running is via Docker:
```bash
docker-compose up -d mongodb redis
```

### 2. Backend (Scrapers)
Scrapers ingest data directly into MongoDB. Ensure you have Python 3.10+ installed.
```bash
# Install dependencies
pip install -r requirements.txt

# Run MD Computers Scraper (Example)
cd Backend/Data_Collection/Scrapers/MD_computers
python Bulk_data.py --all
python Async_Scraper.py --all

# Run PrimeABGB Scraper (Example)
cd ../PrimeABGB
python Bulk_data.py
python Async_Scraper.py
```

### 3. Frontend (Web UI)
The frontend serves both the dashboard and the data API.
```bash
cd Frontend
npm install
npm run dev
```
Accessible at: `http://localhost:3000`

---

## 🛠️ Configuration

Customizing the environment is done via `.env.local` files:

**Frontend (`Frontend/.env.local`):**
```env
MONGODB_URI=mongodb://localhost:27017/loop-pc-builder
REDIS_URL=redis://localhost:6379/0
```

---

## 📝 Troubleshooting & Notes

- **Redis Connectivity**: If you see `ConnectionError`, ensure the Redis container is running (`docker-compose up -d redis`).
- **Missing Dependencies**: If the frontend fails to build, run `npm install` again to ensure `ioredis` and other peer dependencies are fulfilled.
- **Scraper Ingest**: Scrapers save raw JSON snapshots in their respective `data/` folders before processing them into MongoDB.

---

## 📄 License
MIT © 2026 Loop PC Builder
