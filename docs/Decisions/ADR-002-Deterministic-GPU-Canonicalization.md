# ADR-002: Deterministic GPU Canonicalization Engine

* **Status:** Accepted (Implemented & Verified)
* **Date:** September 2026
* **Deciders:** Agam Ramteke
* **Implementation File:** `Backend/Data_Collection/Pipelines/gpu_matcher.py`
* **Test File:** `Backend/Data_Collection/Pipelines/test_gpu_matcher.py`
* **Related Issues:** [Issue #6](https://github.com/Agam-Ramteke/loop-pc-builder/issues/6)

---

## Context & Problem Statement

Retailer graphics card titles are heavily polluted with marketing keywords, AIB brand identifiers, cooling variants, factory overclocking acronyms, and localized spelling errors:
- *"Colorful GeForce RTX 5060 Ti Battle AX DUO 16GB-V"*
- *"Gigabyte RTX 5060 Ti Windforce OC 16GB GDDR7"*

Fuzzy string matching algorithms (e.g. Levenshtein distance, token sort ratio) frequently produce false positives between closely named silicon variants. Conflating an **RTX 5060 Ti 8GB** with an **RTX 5060 Ti 16GB**, or an **RTX 3050 6GB (70W, no external power)** with an **RTX 3050 8GB (130W, 8-pin power)** breaks hardware compatibility advice and misleads pricing comparisons.

## Decision

Implement a **strict 4-stage deterministic matching engine** without fuzzy matching or probabilistic heuristics:
1. **Stage 1 (Spec Table Extraction):** Check structured specification attributes (`Chip Series`, `GPU Model`).
2. **Stage 2 (Title Regex Extraction):** Parse product names against rigid regex patterns for NVIDIA (`GeForce RTX/GTX/GT`), AMD (`Radeon RX`), and Intel (`Arc A/B series`).
3. **Stage 3 (VRAM Disambiguation):** Explicitly extract memory size (`_VRAM_RE`) to isolate capacity-split hardware variants.
4. **Stage 4 (Normalized Key Lookup):** Resolve against a curated dictionary of canonical identifiers.

If a listing does not cleanly match a consumer GPU rule, the matcher returns `None` rather than guessing.

## Consequences

* **Positive:**
  - Zero false-positive variant conflation.
  - 100% test pass rate across 46 unit test cases covering edge cases across NVIDIA, AMD, and Intel Arc.
  - Achieved a 98.5% match rate (715 / 726) across live retailer GPU listings in MongoDB.
  - Enterprise/workstation cards (e.g. Radeon AI PRO R9700) are cleanly rejected and left unpolluted by desktop rules.
* **Trade-offs:**
  - New GPU generations require adding regex patterns and canonical IDs to the reference dictionary.
