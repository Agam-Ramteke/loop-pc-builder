# PostgreSQL Migration Notes

This repo still serves data from MongoDB today, but the next durable data layer should be PostgreSQL or Supabase with a two-layer model:

1. Canonical chip tables for reusable silicon-level facts.
2. Retailer product tables for store-specific SKUs, price, stock, and presentation.

The new schema lives in `Backend/db/schema.sql`, and the current bridge script lives in `Backend/scripts/export_postgres_seed.py`.

## Why this split

- GPUs now clearly have many retailer variants for the same chip, so deduplicating them into `gpu_chips` avoids repeated specs and makes compatibility logic cleaner.
- CPUs are mostly one chip per listing today, but the field explosion in raw specs still benefits from canonicalization into stable columns.
- The audit fields on chip tables (`source_product_name`, `source_product_id`, `source_specifications`, `variant_count`) make spot-checking and manual QA much easier during migration.

## Current staging flow

1. Keep scraping into MongoDB as-is so the frontend and scrapers stay stable.
2. Run `python Backend/scripts/export_postgres_seed.py` to generate Postgres-ready JSON seeds.
3. Load those JSON files into PostgreSQL tables created from `Backend/db/schema.sql`.
4. Cut the frontend and API over after the relational data looks clean enough.

Generated output lands in `Backend/generated_data/postgres/`:

- `gpu_chips.json`
- `gpu_products.json`
- `cpu_chips.json`
- `cpu_products.json`
- `manifest.json`

## GPU normalization rule

The exporter groups GPU products by extracted chip name, then picks the variant with the densest populated `specifications` object as the chip representative. That representative becomes the source of truth for the canonical chip row, while all raw retailer listings still remain in `gpu_products`.

## CPU normalization rule

CPU normalization is alias-driven rather than variant-driven. The exporter maps noisy raw spec keys into canonical CPU fields such as `socket`, `cores_total`, `threads`, `tdp_w`, `memory_type`, and `pcie_version`, then emits chip records plus product rows.

## Other components

The same two-layer idea still applies, but not every category needs a literal "chip" table:

| Component | Canonical identity | Product layer |
| --- | --- | --- |
| RAM | Speed + capacity + type | Retail SKU |
| PSU | Wattage + efficiency tier | Retail SKU |
| Storage | Controller + NAND + capacity | Retail SKU |
| Motherboard | Usually direct SKU normalization is enough | Retail SKU |
| Cabinet | Usually direct SKU normalization is enough | Retail SKU |
| CPU Cooler | Usually direct SKU normalization is enough | Retail SKU |

For motherboards, cabinets, and coolers, a single normalized product table is probably enough unless later recommendation logic proves otherwise.
