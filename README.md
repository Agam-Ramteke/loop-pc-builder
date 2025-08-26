# loop-pc-builder
An intelligent PC part picker and build recommendation system for the Indian market

# Loop – Smart PC Builder & Recommendation System 🇮🇳

LOOP is a PC building & recommendation platform tailored for the Indian market.  
It aggregates prices from Indian retailers (Amazon, Flipkart, PrimeABGB, MDComputers, Vedant, etc.), checks compatibility, and recommends components using ML.

> Status: Early Development – Currently focusing on **data collection (APIs + web scraping)**

---

## Features (Planned)
- **Data Collection**: Fetch component details & pricing via APIs and scraping  
- **Data Storage**: Store structured data (Postgres) & flexible specs (MongoDB)  
- **Caching Layer**: Use Redis for fast lookups  
- **Recommendation Engine**: ML-based suggestions (future)  
- **PC Builder UI**: Interactive build configurator (future)  
- **Trends & Benchmarks**: Price history, performance charts (future)  

---

## Current Focus
1. Collect pricing & specs from:
   - Amazon India API (via affiliate program)  
   - Flipkart API (where available)  
   - Retailers (PrimeABGB, MDComputers, Vedant) → WebScraping  

2. Store raw + processed data in **MongoDB**.  
3. Build a **scraping pipeline** with retry logic & proxy rotation. 
