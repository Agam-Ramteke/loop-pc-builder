# ADR-001: Two-Layer Relational Architecture (PostgreSQL/Supabase)

* **Status:** Accepted (In Progress / Staged)
* **Date:** September 2026
* **Deciders:** Agam Ramteke
* **Context Document:** `docs/postgres_migration.md`
* **Related Issues:** [Issue #10](https://github.com/Agam-Ramteke/loop-pc-builder/issues/10), [Issue #11](https://github.com/Agam-Ramteke/loop-pc-builder/issues/11), [Issue #12](https://github.com/Agam-Ramteke/loop-pc-builder/issues/12), [Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14)

---

## Context & Problem Statement

Loop PC Builder originally stored all scraped data in flat MongoDB collections (`GPUs`, `Processors`, `Motherboards`). While this allowed rapid development without schema constraints, it introduced severe architectural hurdles:
1. **Redundancy & Inconsistency:** 50 retailer listings for an "RTX 5060 Ti 16GB" each duplicated the same architecture, TDP, memory bus, and CUDA core counts. If a spec error existed, fixing it required updating 50 documents.
2. **Impeded Compatibility Checks:** PC compatibility is based on silicon-level facts (socket, memory generation, TDP, PCIe revision), not store-specific product bundles.
3. **Price Comparison Inefficiencies:** Comparing offers across retailers required complex runtime fuzzy grouping.

## Decision

Adopt a **Two-Layer Relational Architecture** implemented in PostgreSQL (`Backend/db/schema.sql`):

1. **Silicon / Canonical Layer (`gpu_chips`, `cpu_chips`):**
   - Single row per unique hardware chip.
   - Stores immutable physical/architectural truths: TDP, die size, core count, memory bus width, socket, VRAM capacity.
   - Audit columns (`source_product_name`, `source_specifications`, `variant_count`) preserve traceability.
2. **Product / Listing Layer (`gpu_products`, `cpu_products`):**
   - Stores retailer SKUs with foreign key references (`chip_id REFERENCES gpu_chips(id)`).
   - Stores commercial attributes: price (INR), availability, product URL, retailer name, cooling brand, and custom card length.

## Staged Migration Strategy

To avoid breaking the production web app:
1. Scrapers continue ingesting into MongoDB `PC_Parts`.
2. `Backend/scripts/export_postgres_seed.py` transforms MongoDB documents into normalized relational JSON seeds.
3. `Backend/scripts/load_postgres_seed.py` loads seeds into PostgreSQL staging tables.
4. Next.js API read path will switch via feature flag once relational benchmarks demonstrate query parity.

## Consequences

* **Positive:**
  - True multi-retailer price comparison for identical chips.
  - Clean, performant compatibility queries using indexed foreign keys.
  - Zero specification duplication across retailer listings.
* **Trade-offs:**
  - Requires explicit transformation and normalization step before data lands in relational tables.
  - Requires maintaining temporary dual-store bridge until full cutover.
