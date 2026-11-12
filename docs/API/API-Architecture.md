# API — Architecture & Serving Layer

This document details the unified component API serving the **Loop PC Builder** frontend ([`Frontend/src/app/api/components/route.ts`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Frontend/src/app/api/components/route.ts)), its caching layer, and the staged migration to PostgreSQL.

---

## 🌐 Endpoint Specification: `GET /api/components`

The API serves paginated, filtered, and sorted PC components across all hardware categories.

### Supported Query Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `category` | `string` | *(Required)* | Component category: `processors`, `gpus`, `motherboards`, `ram`, `storage`, `smps`, `cabinets`, `cpucoolers`. |
| `search` | `string` | `null` | Free-text search term matched against product title, brand, and normalized specifications. |
| `inStockOnly`| `boolean` | `false` | When `true`, filters to items with active inventory. |
| `minPrice` | `number` | `null` | Lower price threshold in INR. |
| `maxPrice` | `number` | `null` | Upper price threshold in INR. |
| `sort` | `string` | `null` | Sorting criterion: `priceAsc`, `priceDesc`, or `name`. |
| `page` | `integer`| `1` | Page offset index. |
| `limit` | `integer`| `24` | Items per page (standard pagination window). |

---

## ⚡ Active Pipeline & Redis Caching

```
Client Request: GET /api/components?category=gpus&page=1&sort=priceAsc
                             │
                             ▼
              [Check Redis Cache (120s TTL)]
                 │                     │
           [Cache Hit]            [Cache Miss]
                 │                     │
          Return JSON (<10ms)          ▼
                          [MongoDB Aggregation Pipeline]
                          • $match: category & inStock filter
                          • $addFields: dynamic price sanitization
                          • $match: minPrice / maxPrice
                          • $sort: requested sort order
                          • $facet: pagination slicing + total count
                                       │
                                       ▼
                          [Write to Redis Cache]
                                       │
                                       ▼
                               Client Response
```

### Response Payload Structure
```json
{
  "items": [
    {
      "id": "673412a...",
      "name": "Gigabyte RTX 5060 Ti Windforce OC 16GB",
      "brand": "Gigabyte",
      "price": 42999,
      "originalPrice": 48999,
      "discountPercent": 12,
      "inStock": true,
      "url": "https://www.primeabgb.com/...",
      "imageUrl": "/product_images/gigabyte-rtx-5060-ti.jpg",
      "specs": {
        "Memory Size": "16 GB",
        "Memory Type": "GDDR7",
        "Length": "281 mm"
      },
      "canonicalGpuId": "rtx_5060_ti_16gb"
    }
  ],
  "total": 715,
  "page": 1,
  "limit": 24,
  "totalPages": 30
}
```

---

## 🔒 Open PR #2 & Input Sanitization

* **Pull Request:** [PR #2: Sanitize pagination and numeric query parsing in /api/components](https://github.com/Agam-Ramteke/loop-pc-builder/pull/2)
* **Improvements Introduced:**
  - Adds `parsePositiveInt` to clamp `page` to `≥ 1` and cap `limit` at a maximum of `100` to prevent denial-of-service memory exhaustion.
  - Adds `parseOptionalNumber` to treat malformed or negative prices as `null` instead of propagating `NaN` into MongoDB queries.
* **Status:** Under review for Week 4 ([Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17)).

---

## 🔀 Staged PostgreSQL Cutover Plan ([GitHub Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14))

To safely transition the read path from MongoDB to the two-layer PostgreSQL schema:
1. **Adapter Interface:** Create a common `ComponentDataAdapter` interface implemented by both `MongoAdapter` and `PostgresAdapter`.
2. **Feature Flagging:** Introduce `NEXT_PUBLIC_DB_BACKEND = "mongodb" | "postgres"` in environment configuration.
3. **Query Parity & Benchmarking:**
   - Benchmark PostgreSQL joins (`gpu_chips` JOIN `gpu_products`) against MongoDB aggregation pipelines ([Issue #13](https://github.com/Agam-Ramteke/loop-pc-builder/issues/13)).
   - Verify pagination ordering, stock filters, and price ranges match identical outputs.
4. **Guarded Cutover:** MongoDB remains the production fallback until staging validation completes with zero regressions.

---

## 🔗 Related Documentation & Issues
- [[Architecture/System-Overview|System Overview]]
- [[Decisions/ADR-001-Two-Layer-Relational-Schema|ADR-001: Two-Layer Relational Schema]]
- **Tracking Issues:**
  - [Issue #13](https://github.com/Agam-Ramteke/loop-pc-builder/issues/13): Benchmark PostgreSQL queries against current Mongo catalog API (P1)
  - [Issue #14](https://github.com/Agam-Ramteke/loop-pc-builder/issues/14): Prepare guarded `/api/components` PostgreSQL read-path cutover (P0)
  - [Issue #17](https://github.com/Agam-Ramteke/loop-pc-builder/issues/17): Resolve frontend lint/type warnings and review open API PR (P1)
