# Data Pipeline — Data Flow & Lifecycle

This document explains how data moves through **Loop PC Builder**, from external retailer catalogs and reference databases to normalized storage and user-facing APIs.

---

## 🌊 End-to-End Data Pipeline

```
[Retailer Catalog HTML]          [TechPowerUp Specs HTML]
          │                                  │
          ▼                                  ▼
   PrimeABGB / EliteHubs             TPU CPU / GPU Scrapers
   (Bulk_data.py)                    (scraper.py)
          │                                  │
          ▼                                  ▼
   [Listing Sync & Price Delta]      [Raw Reference JSON/HTML]
          │                                  │
          ▼                                  ▼
   [gpu_matcher.py]                  [raw_cpu_reference]
   (Attach canonical_gpu_id)         [raw_gpu_reference]
          │                                  │
          ▼                                  ▼
┌────────────────────────────────────────────────────────┐
│                   MONGODB (PC_Parts)                   │
│  • GPUs (726 docs)        • canonical_gpus (645 docs)  │
│  • Processors (162 docs)  • raw_cpu_reference (539)   │
│  • Motherboards (638 docs)• raw_gpu_reference (95)     │
│  • RAM (227 docs)                                      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           │ ──> [Current API Read Path: Next.js + Redis]
                           │
                           ▼
          [Backend/scripts/export_postgres_seed.py]
                           │
                           ▼
          [Backend/generated_data/postgres/]
          • gpu_chips.json      • gpu_products.json
          • cpu_chips.json      • cpu_products.json
          • manifest.json
                           │
                           ▼
          [Backend/scripts/load_postgres_seed.py]
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│               POSTGRESQL (loop_pc_builder)             │
│  • gpu_chips (64 rows)    • gpu_products (773 rows)    │
│  • cpu_chips (138 rows)   • cpu_products (157 rows)    │
└────────────────────────────────────────────────────────┘
```

---

## 🔄 Ingestion & Transformation Stages

### Stage 1: Listing Detection & Price Delta Updates
1. Listing URLs are fetched concurrently.
2. Prices and stock status are extracted directly from catalog summary cards.
3. Fast in-memory comparison checks whether the item already exists in MongoDB.
4. MongoDB `bulk_write` executes atomic `$set` updates for `price`, `in_stock`, and `last_seen_date` without needing to re-fetch heavy product detail pages.

### Stage 2: Detail Specification Crawl & Canonical Matching
1. Only products flagged as newly inserted or lacking technical specifications are placed in the detail fetch queue.
2. Detail tables are parsed into nested JSON key-value pairs (`specifications`).
3. For GPUs:
   - `gpu_matcher.py` is invoked with the product title and parsed specifications.
   - It performs 4-stage matching against the `canonical_gpus` collection.
   - If matched, the document is enriched with:
     ```json
     {
       "canonical_gpu_id": "rtx_5060_ti_16gb",
       "canonical_match_confidence": 0.95,
       "brand": "Gigabyte",
       "card_length_mm": 281,
       "slot_width": 2.5
     }
     ```
   - If no match occurs (e.g. enterprise workstation cards), the raw product is preserved without a canonical ID.

### Stage 3: Relational Seed Generation (`export_postgres_seed.py`)
To bridge MongoDB and PostgreSQL, a deterministic bridge script translates semi-structured documents into strict two-layer relational structures:
- **GPU Normalization Rule:** Products are grouped by extracted chip name. The variant with the densest populated specification object is selected as the representative silicon record (`gpu_chips`), and each retail SKU becomes a row in `gpu_products` linked by `chip_id`.
- **CPU Normalization Rule:** Noisy, non-standardized retailer specification keys (e.g. "Socket Type", "CPU Socket", "Platform") are mapped to canonical columns (`socket`, `cores_total`, `threads`, `tdp_w`, `memory_type`) using dictionary aliases.

### Stage 4: Relational Seed Loading (`load_postgres_seed.py`)
- Reads generated JSON files from `Backend/generated_data/postgres/`.
- Inserts chips first (generating stable UUIDs via `pgcrypto`).
- Inserts products linked to parent `chip_id` references with foreign key integrity.

---

## 🗄️ Utility Scripts in `Backend/scripts/`

| Script | Purpose | Status |
| :--- | :--- | :--- |
| `export_postgres_seed.py` | Transforms MongoDB documents into PostgreSQL relational JSON seed files. | Implemented & verified |
| `load_postgres_seed.py` | Loads exported JSON seeds into PostgreSQL database (`loop_pc_builder`). | Implemented & verified |
| `cpu_schema_audit.py` | Audits raw retailer CPU specs against target relational schema fields. | Implemented & verified |
| `ensure_mongo_indexes.py` | Creates indexes on `canonical_gpu_id`, `url`, `Product Name`, and `price`. | Implemented |

---

## 🔗 Related Documentation & Issues
- [[Architecture/System-Overview|System Overview]]
- [[GPU-Normalization/Canonicalization|GPU Normalization & Matching]]
- [[Decisions/ADR-001-Two-Layer-Relational-Schema|ADR-001: Two-Layer Relational Schema]]
- **Tracking Issues:**
  - [Issue #10](https://github.com/Agam-Ramteke/loop-pc-builder/issues/10): Define canonical chip versus retailer-product data contracts (P2)
  - [Issue #11](https://github.com/Agam-Ramteke/loop-pc-builder/issues/11): Generate and validate PostgreSQL GPU/CPU seed exports (P0)
  - [Issue #12](https://github.com/Agam-Ramteke/loop-pc-builder/issues/12): Load PostgreSQL staging schema and validate data integrity (P0)
