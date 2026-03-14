# Loop – PC Part Picker (India)

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
  - **Premium Interactions**: Custom animated sorting dropdowns, tactile pagination with motion-feedback, and streamlined category navigation.
  - **Search & Filter**: Refactored search engine with URL state persistence and integrated "One-Click Clear" functionality.
  - **Performance Optimized**: Uses CSS blend modes for product images to avoid expensive background removal logic.
  - **Dynamic Architecture**: Built on **Next.js 16 (App Router)** and **React 19**.
- **Robust API & Caching**
  - Unified data API at `/api/components` using MongoDB aggregations.
  - **Redis Cache Layer**: High-speed caching (sub-10ms response) for product searches and API rate-limiting protection.

---

## 🏗️ Project Structure

```text
├── Backend/                 # Python Data Ingestion Layer
│   ├── .venv/               # Isolated Service Dependencies
│   ├── requirements.txt     # Backend specific packages
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
The backend now maintains its own isolated environment inside the `/Backend` directory.

```bash
cd Backend
# Create and activate environment (if not already done)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run Scrapers
cd Data_Collection/Scrapers/MD_computers
python Async_Scraper.py --all
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
