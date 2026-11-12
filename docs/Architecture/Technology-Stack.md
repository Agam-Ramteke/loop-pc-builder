# Architecture — Technology Stack

This document enumerates the languages, libraries, runtimes, database systems, and infrastructure tools powering the **Loop PC Builder** project.

---

## 🐍 Backend Ingestion & Processing

| Component | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Language Runtime** | Python | `3.12.x` | Core backend runtime for scrapers and data pipelines. |
| **Browser Automation** | Playwright (async) | `1.40+` | Headless Chromium automation for dynamic JavaScript rendering and anti-bot mitigation. |
| **HTTP Client** | `curl_cffi` / `aiohttp` | Current | TLS fingerprint impersonation (Chrome) and decoupled asynchronous asset downloads. |
| **HTML Parsing** | BeautifulSoup4 | `4.12+` | Parsing DOM trees, WooCommerce tables, and TechPowerUp specifications. |
| **Database Driver** | PyMongo | `4.6+` | Connection pooling and bulk operations (`UpdateOne`, `$set`, `$setOnInsert`). |
| **Terminal & Logging** | Rich | `13.7+` | Formatted CLI output, execution summaries, tables, and progress bars. |
| **Testing** | Pytest | `9.0+` | Unit testing of matching algorithms, data pipelines, and parsing fixtures. |

---

## 💾 Database & Cache Tier

### 1. MongoDB (Active Primary Store)
- **Version:** `8.2.5`
- **Database Name:** `PC_Parts`
- **Role:** Active operational store serving live Next.js API requests.
- **Key Collections:**
  - `GPUs`: Retail graphics cards with canonical links.
  - `Processors`: Retail CPUs.
  - `Motherboards`, `RAM`: Retail platform components.
  - `canonical_gpus`: Curated silicon reference library.
  - `raw_cpu_reference`, `raw_gpu_reference`: TechPowerUp specification dumps.

### 2. Redis (Cache Layer)
- **Version:** `7.x+` (Docker containerized)
- **Role:** High-speed caching for API responses, search queries, and component filters.
- **Default TTL:** 120 seconds (`CACHE_TTL_SECONDS = 120`).
- **Target Latency:** Sub-10ms response for cached query keys.

### 3. PostgreSQL / Supabase (Staging / Target Store)
- **Version:** PostgreSQL `16+` with `pgcrypto` extension.
- **Database Name:** `loop_pc_builder`
- **Role:** Target relational store under staged migration. Eliminates spec redundancy via normalized silicon chip tables (`gpu_chips`, `cpu_chips`) and retailer product tables (`gpu_products`, `cpu_products`).

---

## 🌐 Frontend & Web Application

| Component | Technology | Version | Purpose / Role |
| :--- | :--- | :--- | :--- |
| **Framework** | Next.js (App Router) | `16.1.6` | Server-side rendering, React Server Components, and unified API routes (`/api/components`). |
| **UI Library** | React | `19.2.3` | Core declarative UI layer. |
| **Styling** | Tailwind CSS | `v4` | Utility-first styling with dark/light theme tokens and glassmorphism. |
| **Animation** | Framer Motion | Current | Physics-based micro-interactions, animated dropdowns, and card transitions. |
| **Icons** | Lucide React | Current | Lightweight, consistent SVG icon set. |
| **Cache Client** | `ioredis` | Current | Node.js Redis client with connection pooling and resilient error handling. |
| **Mongo Client** | `mongodb` | `6.x` | Native Node.js MongoDB driver for aggregation pipelines. |

---

## 🛠️ Infrastructure & Developer Workflow

- **Containerization:** `docker-compose.yml` defining local isolated services for MongoDB (`27017`) and Redis (`6379`).
- **Source Control:** Git hosted on GitHub at `Agam-Ramteke/loop-pc-builder`.
  - Active Development Branch: `Asynchronous-DB-Updation`
- **Task Management:** GitHub Projects & GitHub Issues (#3–#20).
- **Knowledge Base:** Obsidian vault configured at `docs/` with standard Markdown and internal wikilinks.

---

## 🔗 Related Documentation
- [[Architecture/System-Overview|System Overview]]
- [[API/API-Architecture|API Architecture]]
- [[Decisions/ADR-001-Two-Layer-Relational-Schema|ADR-001: Two-Layer Relational Schema]]
