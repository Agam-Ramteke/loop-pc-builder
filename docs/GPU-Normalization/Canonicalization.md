# GPU Normalization — Canonicalization & Matching Engine

This document details the deterministic matching engine implemented in [`Backend/Data_Collection/Pipelines/gpu_matcher.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Pipelines/gpu_matcher.py), which reconciles noisy retailer GPU product names to canonical silicon records.

---

## 🎯 The Normalization Challenge

Retailers list graphics cards with inconsistent titles, mixing brand names, cooler lines, factory overclocks, and memory specs:
- `"Colorful GeForce RTX 5060 Ti Battle AX DUO 16GB-V"`
- `"Gigabyte RTX 5060 Ti Windforce OC 16GB GDDR7"`
- `"ASUS ROG Strix GeForce RTX 5070 Ti 16GB Gaming"`
- `"Sapphire Nitro Plus RX 9060 XT OC 16GB"`

Without normalization:
1. Compatibility engines cannot determine real silicon requirements (power, PCIe lanes, base architecture).
2. Users cannot compare competing retailer prices for the exact same underlying GPU chip.
3. Crucial variant distinctions (such as an RTX 5060 Ti 8GB vs 16GB, or RTX 3050 6GB vs 8GB) risk being conflated.

---

## ⚙️ The 4-Stage Deterministic Algorithm

Rather than relying on non-deterministic LLMs or fuzzy string matching (e.g. Levenshtein distance), `gpu_matcher.py` executes a strict, 4-stage rule-based pipeline:

```
Retailer Product Name + Raw Specifications
                    │
                    ▼
   [Stage 1: Chip Series Extraction]
   Checks parsed retailer spec tables for explicit chip keys
   ("Chip Series", "Graphics Coprocessor", "GPU Model")
                    │
                    ▼
   [Stage 2: Deterministic Regex Title Parsing]
   Matches NVIDIA, AMD, or Intel family + model + suffix:
   • NVIDIA: GeForce (RTX|GTX|GT) (\d{3,5}) (Ti SUPER|SUPER|Ti)?
   • AMD: Radeon (RX) (\d{3,5}) (XT|GRE)?
   • Intel: Arc ([A-B]\d{3,4})
                    │
                    ▼
   [Stage 3: VRAM Disambiguation]
   Extracts memory capacity (e.g. 8GB, 12GB, 16GB, 24GB, 32GB)
   from title or specifications to disambiguate dual-capacity chips
                    │
                    ▼
   [Stage 4: Normalized Key Lookup]
   Normalizes to canonical ID (e.g. "rtx_5060_ti_16gb")
   and queries in-memory lookup index derived from canonical_gpus
                    │
                    ▼
         MatchResult (id, confidence, brand, dimensions)
```

---

## 🧪 Unit Test Verification

The matching engine is validated by an in-memory unit test suite in [`Backend/Data_Collection/Pipelines/test_gpu_matcher.py`](file:///c:/Users/agamr/PycharmProjects/loop-pc-builder/Backend/Data_Collection/Pipelines/test_gpu_matcher.py):

* **Test Result:** **46 / 46 passing tests (100% pass rate)**.
* **Test Categories:**
  - `TestNormalizeKey`: Vendor prefix stripping, case insensitivity, regex cleanup.
  - `TestGenerateCanonicalId`: Suffix formatting, VRAM attachment, multi-token handling.
  - `TestNvidiaMatching`: RTX 5090, 5080, 5070 Ti, 5060 Ti 8GB vs 16GB, 3050 6GB vs 8GB, GTX 1660 Super, GT 1030.
  - `TestAmdMatching`: RX 9070 XT, RX 9060 XT 8GB vs 16GB, RX 6500 XT, RX 7600.
  - `TestIntelMatching`: Arc A770, Arc B580 (Battlemage).
  - `TestBrandExtraction`: ASUS, MSI, Gigabyte, ZOTAC, Colorful, Sapphire, ASRock, PowerColor, XFX, Palit, PNY, Galax, Inno3D.
  - `TestSkuExtraction`: Physical card length (`mm`), display outputs (HDMI/DP), fan configurations.
  - `TestFailSafe`: Empty titles, garbage strings, and enterprise GPU non-matches.

---

## 📊 Live Database Evaluation (MongoDB Snapshot)

When evaluated across all **726 live GPU listings** in MongoDB `PC_Parts.GPUs`:

* **Matched:** **715 / 726 (98.48% match rate)**.
* **Unmatched:** **11 / 726 (1.52%)**.
* **Audit of Unmatched Listings:**
  All 11 unmatched items are enterprise or workstation accelerator cards that were intentionally excluded by the consumer desktop reference filters:
  1. `Asrock AMD Radeon AI PRO R9700 Creator 32GB Graphic Card`
  2. `Sapphire AMD Radeon AI Pro R9700 32GB Graphic Card`
  3. `Sapphire AMD Radeon Pro W7800 48GB GDDR6 Graphic Card`
  4. `ASUS TURBO Radeon AI PRO R9700 32GB Graphic Card`
  5. `NVIDIA RTX PRO 4500 Blackwell Server Edition Graphic Card`
  *(and related workstation variants)*

---

## 🔗 Related Documentation & Issues
- [[Decisions/ADR-002-Deterministic-GPU-Canonicalization|ADR-002: Deterministic GPU Canonicalization]]
- [[Data-Pipeline/Data-Flow|Data Flow & Lifecycle]]
- **Tracking Issues:**
  - [Issue #6](https://github.com/Agam-Ramteke/loop-pc-builder/issues/6): Validate GPU canonical matcher coverage including Intel Arc (P1)
  - [Issue #10](https://github.com/Agam-Ramteke/loop-pc-builder/issues/10): Define canonical chip versus retailer-product data contracts (P2)
