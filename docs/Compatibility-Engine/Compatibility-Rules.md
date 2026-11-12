# Compatibility Engine — Rule Definitions & Specifications

This document defines the deterministic compatibility rules for the **Loop PC Builder** recommendation and validation engine ([GitHub Issue #15](https://github.com/Agam-Ramteke/loop-pc-builder/issues/15) & [Issue #16](https://github.com/Agam-Ramteke/loop-pc-builder/issues/16)).

---

## 🎯 Verification Philosophy

To ensure user trust, compatibility checking follows three core principles:
1. **Deterministic Rules Over Heuristics:** Never guess compatibility when a specification is absent.
2. **Tri-State Classification:** Every evaluation returns one of four explicit states:
   - `COMPATIBLE`: Hard positive confirmation backed by matching specs.
   - `INCOMPATIBLE`: Hard physical or electrical contradiction (prevents assembly or boot).
   - `WARNING`: Assembly works with prerequisites (e.g. BIOS update required, tight clearance).
   - `UNKNOWN`: Missing technical data; advises manual verification without throwing false errors.
3. **Actionable Feedback:** Incompatibility messages must state the exact mismatch (e.g. *"Socket AM5 processor cannot mount on LGA1700 motherboard"*).

---

## 🧩 Rule Matrix

### 1. CPU ⟷ Motherboard Compatibility
- **Socket Match (Hard Check):**
  - The CPU socket (`cpu_chips.socket`) must identically match the motherboard socket (`motherboards.socket`).
  - Examples: `AM5` ⟷ `AM5`, `LGA1700` ⟷ `LGA1700`, `AM4` ⟷ `AM4`.
  - Result if mismatched: `INCOMPATIBLE`.
- **Chipset & BIOS Generation (Advisory Warning):**
  - Certain CPUs require motherboard BIOS revisions released after the board's launch (e.g. Ryzen 5000 on early B450 motherboards, or 14th Gen Intel on Z690/B660 boards).
  - Result: `WARNING` with clear advisory: *"May require BIOS flashback prior to CPU installation"*.

### 2. Memory (RAM) ⟷ Motherboard & CPU Compatibility
- **DDR Generation Match (Hard Check):**
  - CPU supported memory (`cpu_chips.memory_type`) and motherboard memory standard must match the selected RAM module (`DDR4` vs `DDR5`).
  - DDR4 modules cannot physically seat in DDR5 DIMM slots due to key notch differences.
  - Result if mismatched: `INCOMPATIBLE`.
- **Form Factor (Hard Check):**
  - Standard desktop boards require standard `DIMM`. `SO-DIMM` (laptop) is flagged as `INCOMPATIBLE` on desktop boards.
- **Slot Capacity & Count (Hard Check):**
  - Number of selected RAM sticks must be `≤` motherboard available DIMM slots.
  - Total RAM capacity (`GB`) must not exceed motherboard `max_memory_gb`.

### 3. Physical Fit & Case Clearance
- **GPU Length Clearance (Hard Check):**
  - Selected GPU card length (`gpu_products.card_length_mm`) must be `<` case max GPU length clearance (`cabinets.max_gpu_length_mm`).
  - If card length exceeds case clearance: `INCOMPATIBLE`.
  - If clearance delta is `< 10mm`: `WARNING` (tight clearance).
- **CPU Cooler Height Clearance (Hard Check):**
  - Tower air cooler height must be `<` case max cooler height (`cabinets.max_cooler_height_mm`).
  - Liquid cooler (AIO) radiator size (e.g. 240mm, 360mm) must be listed in case supported radiator mounts (top/front).
- **Motherboard Form Factor (Hard Check):**
  - Motherboard form factor (`E-ATX`, `ATX`, `Micro-ATX`, `Mini-ITX`) must be within case supported motherboard sizes.

### 4. Power Supply (PSU) Capacity & Cables
- **Total Power Budget Calculation:**
  $$\text{Estimated Peak Draw} = \text{CPU Max TDP} + \text{GPU TDP} + 75\text{W (Board, Storage, RAM, Fans)}$$
- **Recommended PSU Headroom:**
  $$\text{Target PSU Wattage} \ge \text{Estimated Peak Draw} \times 1.25$$
- **Evaluations:**
  - If PSU rated wattage `< Estimated Peak Draw`: `INCOMPATIBLE` (risk of sudden shutdown or trip).
  - If PSU rated wattage between `Estimated Peak Draw` and `Target PSU Wattage`: `WARNING` (limited headroom for spikes/overclocking).
  - If PSU rated wattage `≥ Target PSU Wattage`: `COMPATIBLE`.
- **GPU Power Connectors:**
  - Verify modern high-power GPUs (e.g. RTX 4080/4090/5080/5090) have matching 12V-2x6 / 12VHPWR power cables or sufficient 8-pin PCIe leads.

---

## 🔗 Related Documentation & Issues
- [[Architecture/System-Overview|System Overview]]
- [[GPU-Normalization/Canonicalization|GPU Normalization]]
- **Tracking Issues:**
  - [Issue #15](https://github.com/Agam-Ramteke/loop-pc-builder/issues/15): Implement CPU–motherboard and RAM compatibility rules (P0)
  - [Issue #16](https://github.com/Agam-Ramteke/loop-pc-builder/issues/16): Add PSU, case and GPU physical-fit compatibility warnings (P1)
  - [Issue #19](https://github.com/Agam-Ramteke/loop-pc-builder/issues/19): Deliver PC builder MVP with compatibility feedback (P1)
