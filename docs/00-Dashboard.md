# 00 — Loop PC Builder Technical Knowledge Base

Welcome to the engineering knowledge base for **Loop PC Builder** (`Agam-Ramteke/loop-pc-builder`), a high-performance PC component pricing aggregator and compatibility builder designed for the Indian hardware market.

> [!NOTE] Knowledge Base Architecture
> This Obsidian vault serves as the authoritative source for **system architecture, technical decisions, implementation notes, and research**.
> Task tracking, assignments, and sprint statuses are authoritatively managed via **GitHub Issues (#3–#20)** and **GitHub Projects**.

---

## 🗺️ Knowledge Map & Quick Links

```
docs/
├── 00-Dashboard.md                     # You are here (Vault Root & Navigation)
├── Architecture/
│   ├── System-Overview.md              # End-to-end pipeline & two-layer architecture
│   └── Technology-Stack.md             # Runtime, frameworks, databases, and tooling
├── Scrapers/
│   └── Scraper-Architecture.md         # PrimeABGB V2, EliteHubs, and TechPowerUp scrapers
├── Data-Pipeline/
│   └── Data-Flow.md                    # Ingestion, delta detection, and seed exports
├── GPU-Normalization/
│   └── Canonicalization.md             # 4-stage deterministic matcher & VRAM disambiguation
├── Compatibility-Engine/
│   └── Compatibility-Rules.md          # CPU-motherboard, RAM, PSU, and clearance rules
├── API/
│   └── API-Architecture.md             # Next.js App Router API, Redis caching, query pipeline
├── Frontend/
│   └── Frontend-Architecture.md        # UI components, styling, image blending, state
├── Decisions/                          # Architecture Decision Records (ADRs)
│   ├── ADR-001-Two-Layer-Relational-Schema.md
│   ├── ADR-002-Deterministic-GPU-Canonicalization.md
│   └── ADR-003-PrimeABGB-V2-Delta-Scraper.md
├── Roadmap/
│   └── Engineering-Roadmap.md          # 30-day plan mapped to GitHub Issues #3–#20
└── Development-Logs/
    └── 2026-11-13-Obsidian-Vault-Bootstrap.md
```

### Core Architecture & System Design
- [[Architecture/System-Overview|System Overview]]: End-to-end data pipeline from raw retail scrapers to Next.js 16 frontend.
- [[Architecture/Technology-Stack|Technology Stack]]: Complete runtime specifications (Python 3.12, Next.js 16, React 19, MongoDB 8, PostgreSQL, Redis).
- [[Decisions/ADR-001-Two-Layer-Relational-Schema|ADR-001 Dual-Layer Relational Model]]: Why silicon facts (`gpu_chips`) are separated from store listings (`gpu_products`).

### Data Ingestion & Hardware Normalization
- [[Scrapers/Scraper-Architecture|Scraper Fleet Architecture]]: Unified PrimeABGB V2 concurrent delta scraper, EliteHubs scraper, and TechPowerUp reference scrapers.
- [[Data-Pipeline/Data-Flow|Data Flow & Ingestion Lifecycle]]: Ingestion stages, delta detection, MongoDB upserts, and PostgreSQL seed generation.
- [[GPU-Normalization/Canonicalization|GPU Normalization & Matching]]: 4-stage deterministic matching engine (46/46 unit tests passing, 98.5% live match rate).
- [[Decisions/ADR-002-Deterministic-GPU-Canonicalization|ADR-002 Deterministic Matching]]: Why fuzzy matching is excluded from canonical identification.
- [[Decisions/ADR-003-PrimeABGB-V2-Delta-Scraper|ADR-003 PrimeABGB V2 Scraper]]: Deprecation of `Async_Scraper.py` in favor of concurrent delta-only scraping in `Bulk_data.py`.

### Application Services & Rules
- [[API/API-Architecture|API Architecture]]: Unified `/api/components` endpoint, MongoDB aggregation pipelines, Redis caching, and planned PostgreSQL cutover.
- [[Frontend/Frontend-Architecture|Frontend Architecture]]: Glassmorphic UI, Starfield canvas, component browser, and builder interface.
- [[Compatibility-Engine/Compatibility-Rules|Compatibility Rules Engine]]: Sockets, memory generations, TDP budgets, and physical clearance checks.

---

## 📊 System State & Database Snapshot

> [!NOTE] Snapshot Observation Notice
> The metrics below represent verified local database snapshots observed on **September 27, 2026** and **November 13, 2026** (MongoDB 8.2.5 local instance). They are historical checkpoints, not live production telemetry.

### MongoDB `PC_Parts` Collections

| Collection | Role | Verified Count | Integrity / Status |
| :--- | :--- | :---: | :--- |
| `raw_cpu_reference` | TechPowerUp reference CPUs (≥ 2018) | **539** | 100% complete; 0 duplicate slugs, 0 duplicate names. |
| `raw_gpu_reference` | TechPowerUp reference GPUs (≥ 2017) | **95** | 38.8% complete (95/245 discovered; Issue #3 in progress). |
| `canonical_gpus` | Consumer desktop GPU canonical library | **645** | Filtered from 1,908 reference records. |
| `GPUs` | Retailer GPU listings (PrimeABGB) | **726** | **715 matched with `canonical_gpu_id` (98.5%)**; 11 enterprise cards intentionally excluded. |
| `Processors` | Retailer CPU listings (PrimeABGB/EliteHubs) | **162** | Active catalog listings. |
| `Motherboards` | Retailer Motherboard listings | **638** | Active catalog listings. |
| `RAM` | Retailer Memory listings | **227** | Active catalog listings. |

### PostgreSQL Staging Database (`loop_pc_builder`)

| Table | Current Staged Rows | Target Layer |
| :--- | :---: | :--- |
| `gpu_chips` | **64** | Canonical silicon specifications |
| `gpu_products` | **773** | Retail listings / SKUs linked by `chip_id` |
| `cpu_chips` | **138** | Canonical CPU specifications |
| `cpu_products` | **157** | Retail listings / SKUs linked by `chip_id` |

---

## 🎯 30-Day Engineering Roadmap Summary

Detailed issue tracking and dependencies are documented in [[Roadmap/Engineering-Roadmap|Engineering Roadmap]] and tracked on GitHub:

* **Week 1: Reference Data Completeness & Scraper Reliability**
  * `[W1]` [Issue #3](https://github.com/Agam-Ramteke/loop-pc-builder/issues/3): Complete TechPowerUp GPU reference scraping (95/245 → 245/245) `P0`
  * `[W1]` [Issue #4](https://github.com/Agam-Ramteke/loop-pc-builder/issues/4): Add GPU reference scrape coverage and quality audit `P0`
  * `[W1]` [Issue #5](https://github.com/Agam-Ramteke/loop-pc-builder/issues/5): Audit PrimeABGB V2 delta scraper metrics and failure recovery `P1`
  * `[W1]` [Issue #6](https://github.com/Agam-Ramteke/loop-pc-builder/issues/6): Validate GPU canonical matcher coverage including Intel Arc `P1`
  * `[W1]` [Issue #7](https://github.com/Agam-Ramteke/loop-pc-builder/issues/7): Sync Obsidian documentation with current scraper architecture `P1`
* **Week 2: Scraper Fleet Hardening & Postgres Seeds**
  * `[W2]` [Issue #8](https://github.com/Agam-Ramteke/loop-pc-builder/issues/8): Complete missing retailer component categories `P1`
  * `[W2]` [Issue #9](https://github.com/Agam-Ramteke/loop-pc-builder/issues/9): Harden scraper regression tests and idempotent upserts `P2`
  * `[W2]` [Issue #10](https://github.com/Agam-Ramteke/loop-pc-builder/issues/10): Define canonical chip versus retailer-product data contracts `P2`
  * `[W2]` [Issue #11](https://github.com/Agam-Ramteke/loop-pc-builder/issues/11): Generate and validate PostgreSQL GPU/CPU seed exports `P0`
* **Week 3: Relational Database Migration & Compatibility Engine**
  * `[W3]` [Issue #12](https://github.com/Agam-Ramteke/loop-pc-builder/issues/12): Load PostgreSQL staging schema and validate data integrity `P0`
  * `[W3]` [Issue #13](https://github.com/Agam-Ramteke/loop-pc-builder/issues/13): Benchmark PostgreSQL queries against current Mongo catalog API `P1`
  * `[W3]` [Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14): Prepare guarded `/api/components` PostgreSQL read-path cutover `P0`
  * `[W3]` [Issue #15](https://github.com/Agam-Ramteke/loop-pc-builder/issues/15): Implement CPU–motherboard and RAM compatibility rules `P0`
  * `[W3]` [Issue #16](https://github.com/Agam-Ramteke/loop-pc-builder/issues/16): Add PSU, case and GPU physical-fit compatibility warnings `P1`
* **Week 4: Application Polish, Offer Comparison, PC Builder MVP & CI**
  * `[W4]` [Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17): Resolve frontend lint/type warnings and review open API PR `P1`
  * `[W4]` [Issue #18](https://github.com/Agam-Ramteke/loop-pc-builder/issues/18): Build canonical component browser with retailer offer comparison `P1`
  * `[W4]` [Issue #19](https://github.com/Agam-Ramteke/loop-pc-builder/issues/19): Deliver PC builder MVP with compatibility feedback and shareable builds `P1`
  * `[W4]` [Issue #20](https://github.com/Agam-Ramteke/loop-pc-builder/issues/20): Add CI, Docker integration smoke tests and portfolio-ready README `P1`

---

## 🛡️ Repository & Vault Integrity Rules
1. **GitHub Issues is Authoritative for Tasks:** Never track tasks in ad-hoc local files. Refer to [[Roadmap/Engineering-Roadmap|Engineering Roadmap]] and link GitHub Issues.
2. **Obsidian is Authoritative for Architecture:** Changes to schema, scrapers, normalization, or APIs must be reflected here.
3. **Preserve MongoDB While PostgreSQL is Staged:** Never alter production API read paths until PostgreSQL benchmarks and feature flags validate parity.
4. **No Unverified Completions:** Tasks are marked complete only after code execution, database count checks, or test suite passes.
