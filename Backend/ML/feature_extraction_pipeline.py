"""
Feature Extraction Pipeline — Loop PC Builder
==============================================
GPU extractor tuned to PrimeABGB document schema.
All other extractors preserved and intact for later tuning.

Source: PrimeABGB only (MD Computers GPU docs removed from DB).

Real PrimeABGB GPU field names used:
    MEMORY            → "16GB GDDR7"        (VRAM size + type in one field)
    INTERFACE         → "PCI Express® Gen 5"
    POWER CONSUMPTION → "360W"              (actual TDP)
    RECOMMENDED PSU   → "850 W"
    CARD DIMENSION (MM) → "338 x 140 x 50 mm"  (length x width x height)
    POWER CONNECTORS  → "16-pin x 1"
    CUDA® CORES       → "10752 Units"
    CORE CLOCKS       → "Boost: 2700 MHz ..."
    MEMORY SPEED      → "30 Gbps"           (bandwidth, not clock — skip for compat)
    MEMORY BUS        → "256-bit"

Usage:
    python feature_extraction_pipeline.py
    python feature_extraction_pipeline.py --collection GPUs
    python feature_extraction_pipeline.py --verbose
"""

import os
import re
import json
import logging
import argparse
from datetime import datetime, timezone, date
from typing import Any, Optional
from pymongo import MongoClient

# ─────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────
MONGO_URI  = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME    = "PC_Parts"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

SOURCE_COLLECTIONS = [
    "Processors",
    "Motherboards",
    "RAM",
    "GPUs",
    "SMPS",
    "CpuCoolers",
    "Cabinets",
    "Storage",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  JSON SERIALISER
# ─────────────────────────────────────────────────────────────────────
class _Encoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        try:
            return str(obj)
        except Exception:
            return super().default(obj)


def _dump(data: Any) -> str:
    return json.dumps(data, cls=_Encoder, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────
#  SPEC READER
# ─────────────────────────────────────────────────────────────────────

def _normalize_spec_key(raw: str) -> str:
    if not isinstance(raw, str):
        return ""
    normalised = re.sub(r"[^A-Za-z0-9]+", " ", raw.upper())
    return re.sub(r"\s+", " ", normalised).strip()


def _spec_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value).strip()
    return ""


def _spec(doc: dict, *keys: str) -> str:
    """
    Case-insensitive lookup across specifications/specs dict, then top-level.
    Returns "" on miss — callers never get None.
    """
    specs: dict = doc.get("specifications") or doc.get("specs") or {}
    specs_ci = {
        k.lower(): v
        for k, v in specs.items()
        if isinstance(k, str)
    }
    specs_normalised: dict[str, Any] = {}
    for raw_key, value in specs.items():
        normalised_key = _normalize_spec_key(raw_key)
        if normalised_key and normalised_key not in specs_normalised:
            specs_normalised[normalised_key] = value

    for key in keys:
        val = specs_ci.get(key.lower())
        text = _spec_text(val)
        if text:
            return text
        normalised_key = _normalize_spec_key(key)
        val = specs_normalised.get(normalised_key)
        text = _spec_text(val)
        if text:
            return text
        val = doc.get(key)
        text = _spec_text(val)
        if text:
            return text
    return ""


def _is_na(raw: str) -> bool:
    return raw.strip().upper() in {"N/A", "NA", "NONE", "-", "--", ""}


def _price_number(doc: dict) -> float:
    price = doc.get("price")
    if not price:
        return 0.0
    raw = (
        price.get("discounted") or price.get("original") or ""
        if isinstance(price, dict)
        else str(price)
    )
    cleaned = re.sub(r"[₹Rs.,\s]", "", raw)
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(m.group()) if m else 0.0


# ─────────────────────────────────────────────────────────────────────
#  DOMAIN PARSERS  (shared across all extractors)
# ─────────────────────────────────────────────────────────────────────

def _socket(raw: str) -> str:
    if not raw or _is_na(raw):
        return ""
    s = raw.upper().strip()
    s = re.sub(r"^(SOCKET|FCPGA|FCLGA)\s*", "", s).strip()
    s = re.sub(r"\s+", "", s)
    s = re.sub(r"\(.*?\)", "", s).strip()
    s = s.replace("FCLGA", "LGA")
    return s


def _socket_list(raw: str) -> list[str]:
    if not raw or _is_na(raw):
        return []
    sockets: list[str] = []
    for part in re.split(r"[,/|；\s]+", raw):
        norm = _socket(part.strip())
        if norm and norm not in sockets:
            sockets.append(norm)
    return sockets


def _infer_socket_from_name(name: str) -> str:
    n = name.upper()
    if re.search(r"RYZEN\s+[3579]\s+[789]\d{3}", n):                  return "AM5"
    if re.search(r"RYZEN\s+[3579]\s+[789]\d{3}X3D", n):               return "AM5"
    if re.search(r"RYZEN\s+[3579]\s+[1-6]\d{3}", n):                  return "AM4"
    if re.search(r"CORE\s+(ULTRA\s+)?[I579]\d?[\s-]1[3456]\d{3}", n): return "LGA1700"
    if re.search(r"CORE\s+[I579][\s-]1[012]\d{3}", n):                return "LGA1200"
    if re.search(r"I[3579]-9\d{3}", n):                                return "LGA1151"
    if re.search(r"I[3579]-[78]\d{3}", n):                             return "LGA1151"
    return ""


def _ddr_type(raw: str) -> str:
    if not raw or _is_na(raw):
        return ""
    s = raw.upper()
    pc = re.search(r"PC(\d)", s)
    if pc:
        return f"DDR{pc.group(1)}"
    m = re.search(r"(LPDDR\d X?|DDR\d)", s)
    return m.group(1).strip() if m else ""


def _speed_mhz(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None
    s = raw.upper().replace(",", "")
    pc = re.search(r"PC\d-(\d{4,6})", s)
    if pc:
        return int(pc.group(1)) // 8
    m = re.search(r"(\d{3,5})\s*(MHZ|MT/S|MT\b)", s)
    if m:
        v = int(m.group(1))
        if 800 <= v <= 12000:
            return v
    m2 = re.search(r"(\d{3,5})", s)
    if m2:
        v = int(m2.group(1))
        if 800 <= v <= 12000:
            return v
    return None


def _tdp_watts(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None
    m = re.search(r"(\d{1,4})\s*W\b", raw, re.IGNORECASE)
    if m:
        v = int(m.group(1))
        if 5 <= v <= 700:
            return v
    return None


def _psu_watts(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None
    m = re.search(r"(\d{2,4})\s*(W|WATT)", raw, re.IGNORECASE)
    if m:
        v = int(m.group(1))
        if 200 <= v <= 3000:
            return v
    return None


def _form_factor_list(raw: str) -> list[str]:
    results = []
    for part in re.split(r"[,/|]+", raw):
        s = part.strip().upper()
        if not s:
            continue
        if re.search(r"MINI.?ITX|M.?ITX\b|ITX", s):     results.append("Mini-ITX")
        elif re.search(r"MICRO.?ATX|M.?ATX\b|MATX", s): results.append("Micro-ATX")
        elif re.search(r"E.?ATX|EATX|XL.?ATX", s):      results.append("E-ATX")
        elif re.search(r"\bATX\b", s):                   results.append("ATX")
        elif re.search(r"2\.5", s):                      results.append('2.5"')
        elif re.search(r"3\.5", s):                      results.append('3.5"')
        elif re.search(r"M\.?2", s):                     results.append("M.2")
        elif s:
            results.append(part.strip())
    seen: set[str] = set()
    return [x for x in results if not (x in seen or seen.add(x))]  # type: ignore[func-returns-value]


def _mm(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None
    m = re.search(r"(\d{2,4})\s*mm", raw, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d{2,4})", raw)
    if m2:
        v = int(m2.group(1))
        if 50 <= v <= 500:
            return v
    return None


def _gb(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None
    m = re.search(r"(\d+)\s*GB", raw, re.IGNORECASE)
    return int(m.group(1)) if m else None


def _pcie_version(raw: str) -> Optional[float]:
    if not raw or _is_na(raw):
        return None
    m = re.search(r"GEN\s*(\d)", raw, re.IGNORECASE)
    if m:
        return float(m.group(1))
    m2 = re.search(r"(\d+\.\d+)", raw)
    if m2:
        return float(m2.group(1))
    m3 = re.search(r"\b([345])\b", raw)
    if m3:
        return float(m3.group(1))
    return None


def _gpu_memory_features(*values: str) -> tuple[Optional[int], str]:
    vram_gb: Optional[int] = None
    vram_type = ""

    for raw in values:
        if not raw or _is_na(raw):
            continue
        if vram_gb is None:
            size_match = re.search(r"(\d+(?:\.\d+)?)\s*GB", raw, re.IGNORECASE)
            if size_match:
                vram_gb = int(float(size_match.group(1)))
        if not vram_type:
            type_match = re.search(r"(GDDR\d+X?|HBM\d*\w*|LPDDR\dX?)", raw, re.IGNORECASE)
            if type_match:
                vram_type = type_match.group(1).upper()
        if vram_gb is not None and vram_type:
            break

    return vram_gb, vram_type


def _gpu_dimensions_mm(*values: str) -> tuple[Optional[int], Optional[int], Optional[int]]:
    for raw in values:
        if not raw or _is_na(raw):
            continue
        primary = raw.split("/", 1)[0]
        dims = [
            int(round(float(value)))
            for value in re.findall(r"\d+(?:\.\d+)?", primary)
        ]
        dims = [value for value in dims if 20 <= value <= 500]
        if dims:
            length_mm = dims[0]
            width_mm = dims[1] if len(dims) >= 2 else None
            height_mm = dims[2] if len(dims) >= 3 else None
            return length_mm, width_mm, height_mm

    return None, None, None


def _gpu_connector_details(raw: str) -> tuple[Optional[bool], str]:
    if not raw:
        return None, ""
    if _is_na(raw):
        return False, ""

    text = raw.upper().replace("×", "X")
    text = re.sub(r"\s+", " ", text).strip()

    connector_type = ""
    if re.search(r"12V\s*[- ]?\s*2X6|12VHPWR|16\s*[- ]?PIN", text):
        connector_type = "16-pin"
    elif re.search(r"6\+2|8\s*[- ]?PIN", text):
        connector_type = "8-pin"
    elif re.search(r"\b6\s*[- ]?PIN\b", text):
        connector_type = "6-pin"

    count: Optional[int] = None
    count_patterns = [
        r"(\d+)\s*X\s*(?:12V\s*[- ]?\s*2X6|12VHPWR|16\s*[- ]?PIN|8\s*[- ]?PIN|6\s*[- ]?PIN)",
        r"(?:12V\s*[- ]?\s*2X6|12VHPWR|16\s*[- ]?PIN|8\s*[- ]?PIN|6\s*[- ]?PIN)\s*X\s*(\d+)",
    ]
    for pattern in count_patterns:
        match = re.search(pattern, text)
        if match:
            count = int(match.group(1))
            break

    if count is None and connector_type:
        count = 1

    label = connector_type
    if connector_type and count:
        label = f"{connector_type} x{count}"

    return True, label


def _efficiency_tier(raw: str, name: str) -> str:
    combined = (raw + " " + name).upper()
    for tier in ("TITANIUM", "PLATINUM", "GOLD", "SILVER", "BRONZE"):
        if tier in combined:
            return tier.capitalize()
    if "80" in combined and "PLUS" in combined:
        return "Standard"
    return ""


def _modular(raw: str, name: str = "") -> str:
    s = (raw + " " + name).upper()
    if re.search(r"NON.?MODULAR|NOT.?MODULAR", s): return "Non"
    if re.search(r"FULL.?MODULAR",              s): return "Full"
    if re.search(r"SEMI.?MODULAR",              s): return "Semi"
    if "NON"  in s: return "Non"
    if "FULL" in s: return "Full"
    if "SEMI" in s: return "Semi"
    return ""


# ─────────────────────────────────────────────────────────────────────
#  GPU EXTRACTOR  — tuned to PrimeABGB schema
# ─────────────────────────────────────────────────────────────────────
#
#  PrimeABGB field anatomy (from real RTX 5080 doc):
#
#  MEMORY            "16GB GDDR7"
#    → vram_gb=16, vram_type="GDDR7"
#    Both are packed into one field — split on space/digit boundary.
#
#  INTERFACE         "PCI Express® Gen 5"
#    → pcie_gen=5.0
#    Has the registered trademark symbol ® — strip non-ASCII before parsing.
#
#  POWER CONSUMPTION "360W"
#    → tdp_watts=360
#    This is the actual board TDP, not a system recommendation.
#    Note: 360W exceeds the 700W cap in generic _tdp_watts() — raised to 800W.
#
#  RECOMMENDED PSU   "850 W"
#    → psu_recommended_w=850
#    Explicit field — no inference needed for high-end cards.
#    Low-end cards may still be "N/A" → fallback logic retained.
#
#  CARD DIMENSION (MM)  "338 x 140 x 50 mm"
#    → length_mm=338, width_mm=140, height_mm=50
#    Three dimensions packed in one field as "L x W x H mm".
#    Only length matters for case clearance, but extract all three.
#
#  POWER CONNECTORS  "16-pin x 1"
#    → needs_power_connector=True, connector_type="16-pin"
#    Modern high-end GPUs use the 16-pin (12VHPWR) connector.
#    Low-end cards: "N/A" → needs_power_connector=False.
#
#  CUDA® CORES       "10752 Units"
#    → cuda_cores=10752
#    Used to infer GPU tier when TDP is missing (tier inference table below).
#
#  CORE CLOCKS       "Extreme Performance: 2715 MHz (MSI Center) Boost: 2700 MHz ..."
#    → boost_clock_mhz=2700
#    Extract the "Boost:" value — that's the advertised spec.
#    "Extreme Performance" is software OC mode, not the base spec.
#
#  MEMORY SPEED      "30 Gbps"
#    → intentionally not extracted — this is memory bandwidth, not a
#      compatibility field. No comparison needed for the matrix.
#
#  MEMORY BUS        "256-bit"
#    → memory_bus_bit=256
#    Not a compatibility field but useful for the UI display.
def extract_gpu(doc: dict) -> dict:
    raw_memory_type = _spec(doc, "Memory Type", "MEMORY TYPE")
    raw_memory = _spec(doc, "MEMORY", "Memory", "Video Memory", "VRAM", "Graphics Memory", "Graphic Card Memory Size", "Memory Size", "Memory Size/Bus")
    raw_interface = _spec(doc, "Bus Standard", "PCI Express", "Card Bus", "INTERFACE", "PCI EXPRESS", "PCI-E", "Bus Interface", "Bus Type", "Interface")
    raw_tdp = _spec(doc, "POWER CONSUMPTION", "TDP", "Board Power", "Total Graphics Power", "Max Power Consumption", "Power Consumption", "TBP", "Total Board Power")
    raw_psu = _spec(doc, "RECOMMENDED PSU", "Recommended PSU", "Recommended System Power", "Minimum PSU Recommendation", "Recommended Power Supply")
    raw_dimensions = _spec(doc, "CARD DIMENSION (MM)", "Card Dimension", "Card Dimensions", "Card Dimension (mm)", "Dimensions", "Card Length", "Form Factor")
    raw_connectors = _spec(doc, "POWER CONNECTORS", "Power Connectors", "Power Connector", "PCIe Power Connector", "Power Input", "External Power Connector")
    raw_cuda = _spec(doc, "CUDA® CORES", "CUDA CORES", "CUDA Cores", "Shader Units", "Stream Processors")
    raw_clocks = _spec(doc, "CORE CLOCKS", "Core Clocks", "Engine Clock", "Core Clock", "GPU Clock", "Boost Clock", "Base Clock")
    raw_mem_bus = _spec(doc, "MEMORY BUS", "Memory Bus", "Memory Interface", "MEMORY INTERFACE", "Memory Interface Width", "Memory Size/Bus")

    vram_gb, vram_type = _gpu_memory_features(raw_memory, raw_memory_type, doc.get("name", ""))
    
    pcie_gen = None
    if raw_interface and re.search(r"PCI|GEN\s*\d", raw_interface, re.IGNORECASE):
        pcie_raw_clean = re.sub(r"[^A-Za-z0-9.\\s-]", " ", raw_interface)
        pcie_gen = _pcie_version(pcie_raw_clean)

    tdp_watts = None
    if raw_tdp and not _is_na(raw_tdp):
        m = re.search(r"(\d{1,4})\s*W\b", raw_tdp, re.IGNORECASE)
        if m:
            v = int(m.group(1))
            if 5 <= v <= 800:
                tdp_watts = v

    psu_recommended = None
    if raw_psu and not _is_na(raw_psu):
        psu_recommended = _psu_watts(raw_psu)
    if not psu_recommended:
        if tdp_watts:
            psu_recommended = tdp_watts + 150
        elif vram_gb:
            if vram_gb >= 16:   psu_recommended = 850
            elif vram_gb >= 12: psu_recommended = 750
            elif vram_gb >= 8:  psu_recommended = 650
            elif vram_gb >= 6:  psu_recommended = 550
            else:               psu_recommended = 450

    length_mm, width_mm, slot_height_mm = _gpu_dimensions_mm(raw_dimensions)

    needs_power_connector = None
    connector_type = ""
    if raw_connectors:
        if _is_na(raw_connectors):
            needs_power_connector = False
        else:
            needs_power_connector = True
            s = raw_connectors.upper()
            if "16" in s and "PIN" in s: connector_type = "16-pin"
            elif "8" in s and "PIN" in s: connector_type = "8-pin"
            elif "6" in s and "PIN" in s: connector_type = "6-pin"
            count_m = re.search(r"[xX×]\s*(\d+)", raw_connectors)
            if count_m: connector_type += f" x{count_m.group(1)}"

    cuda_cores = None
    if not raw_cuda: raw_cuda = _spec(doc, "CUDA Core", "CUDAZ CORES", "CUDAŽ CORES")
    if raw_cuda and not _is_na(raw_cuda):
        m = re.search(r"(\d[\d,]+)", raw_cuda)
        if m: cuda_cores = int(m.group(1).replace(",", ""))

    boost_clock_mhz = None
    if raw_clocks and not _is_na(raw_clocks):
        boost_m = re.search(r"boost[:\s]+(\d+)\s*MHz", raw_clocks, re.IGNORECASE)
        if boost_m: boost_clock_mhz = int(boost_m.group(1))
        else:
            all_mhz = re.findall(r"(\d+)\s*MHz", raw_clocks, re.IGNORECASE)
            if all_mhz: boost_clock_mhz = int(all_mhz[-1])

    memory_bus_bit = None
    if raw_mem_bus and not _is_na(raw_mem_bus):
        m = re.search(r"(\d+)\s*-?\s*bit", raw_mem_bus, re.IGNORECASE)
        if m: memory_bus_bit = int(m.group(1))

    return {
        "vram_gb": vram_gb,
        "memory_type": vram_type,
        "memory_bus_bit": memory_bus_bit,
        "shader_count": cuda_cores,
        "boost_clock_mhz": boost_clock_mhz,
        "tdp_w": tdp_watts,
        "recommended_psu_w": psu_recommended,
        "pcie_interface": pcie_gen,
        "slot_width": None,
        "card_length_mm": length_mm,
        "directx_version": None,
        "output_ports_json": None,
        "has_ray_tracing": None,
        "gpu_family": None,
        "gpu_vendor": None,
    }


def _compat_socket_list(raw: str) -> list[str]:
    if not raw or _is_na(raw):
        return []

    sockets: list[str] = []
    pattern = re.compile(
        r"(LGA\s*-?\s*(?:\d{3,4}|115X)|LGA(?:\d{3,4}|115X)|AM\s*[2345](?:\+)?|AM[2345](?:\+)?|FM\s*\d(?:\+)?|FM\d(?:\+)?|s?TRX4|s?TR4|s?TR5)",
        re.IGNORECASE,
    )
    for match in pattern.finditer(raw):
        norm = _socket(match.group(1))
        if norm and norm not in sockets:
            sockets.append(norm)

    if sockets:
        return sockets

    for part in re.split(r"[,/|;]+", raw):
        norm = _socket(part.strip())
        if norm and norm not in sockets:
            sockets.append(norm)
    return sockets


def _compat_first_socket(*values: str) -> str:
    for raw in values:
        if not raw or _is_na(raw):
            continue
        sockets = _compat_socket_list(raw)
        if sockets:
            return sockets[0]
        if re.search(r"\b(?:LGA|AM|FM|TR)\b", raw, re.IGNORECASE):
            norm = _socket(raw)
            if norm:
                return norm
        elif re.search(r"\b(?:LGA\s*\d{3,4}|AM\s*[2345]|s?TRX?4|s?TR5)\b", raw, re.IGNORECASE):
            norm = _socket(raw)
            if norm:
                return norm
    return ""


def _compat_ddr_support(*values: str) -> list[str]:
    text = " ".join(str(value) for value in values if value and not _is_na(str(value)))
    if not text:
        return []

    normalized = (
        text.upper()
        .replace("LPDDR5X", "DDR5")
        .replace("LPDDR5", "DDR5")
        .replace("LPDDR4X", "DDR4")
        .replace("LPDDR4", "DDR4")
    )

    supported: list[str] = []

    def add(memory_type: str) -> None:
        if memory_type not in supported:
            supported.append(memory_type)

    for match in re.finditer(r"\bDDR\s*([345])\b", normalized):
        add(f"DDR{match.group(1)}")
    for match in re.finditer(r"\bPC\s*([345])(?:[-\s]?\d+)?\b", normalized):
        add(f"DDR{match.group(1)}")

    if supported:
        return supported

    if "LGA1851" in normalized or re.search(r"CORE\s+ULTRA\s+[3579]\s+2\d{2}[A-Z]?\b", normalized):
        return ["DDR5"]
    if "LGA1700" in normalized or re.search(r"\b(?:CORE\s+)?I[3579][- ]?1[234]\d{3}\b", normalized):
        return ["DDR4", "DDR5"]
    if "AM5" in normalized or re.search(r"RYZEN\s+[3579]\s+[789]\d{3}", normalized):
        return ["DDR5"]
    if "AM4" in normalized or re.search(r"RYZEN\s+[3579]\s+[1-5]\d{3}", normalized):
        return ["DDR4"]
    if any(socket in normalized for socket in ("LGA1200", "LGA1151", "LGA1150", "LGA1155", "LGA1156", "LGA2066", "LGA2011")):
        return ["DDR4"]

    return []


def _compat_dimensions_mm(raw: str) -> list[int]:
    if not raw or _is_na(raw):
        return []
    primary = raw.split("/", 1)[0].replace("×", "x").replace("*", "x")
    dims = [int(round(float(value))) for value in re.findall(r"\d+(?:\.\d+)?", primary)]
    return [value for value in dims if 10 <= value <= 1000]


def _compat_last_dimension_mm(raw: str) -> Optional[int]:
    dims = _compat_dimensions_mm(raw)
    if dims:
        return dims[-1]
    return _mm(raw)


def _compat_first_dimension_mm(raw: str) -> Optional[int]:
    dims = _compat_dimensions_mm(raw)
    if dims:
        return dims[0]
    return _mm(raw)


def _compat_psu_connector_count(raw: str, connector_kind: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None

    text = raw.upper().replace("×", "X").replace("PCI-E", "PCIE")

    if connector_kind == "16pin":
        count_patterns = [
            r"(?:12VHPWR(?:\s*CONNECTORS?)?|12V\s*[- ]?2X6(?:\s*CONNECTORS?)?|PCIE\s*16-?PIN)\s*[:x]?\s*(\d+)",
            r"(?:12VHPWR|12V\s*[- ]?2X6|PCIE\s*16-?PIN)\s*[xX:]\s*(\d+)",
            r"(\d+)\s*[xX]\s*(?:PCIE\s*)?(?:16\s*\(?(?:12\+4)?\)?\s*PIN|12VHPWR|12V\s*[- ]?2X6)(?:\s*PCIE)?",
        ]
        presence_pattern = r"12VHPWR|12V\s*[- ]?2X6|PCIE\s*16-?PIN|16\s*\(?(?:12\+4)?\)?\s*PIN\s*PCIE"
    else:
        count_patterns = [
            r"(?:PCIE\s*CONNECTOR(?:\s*\(6\+2\))?)\s*[:x]?\s*(\d+)",
            r"(?:PCIE\s*(?:6\+2|8)-?PIN)\s*[xX:]\s*(\d+)",
            r"(\d+)\s*[xX]\s*(?:PCIE\s*)?(?:6\+2|8\s*\(6\+2\))\s*PIN(?:\s*PCIE)?",
        ]
        presence_pattern = r"PCIE\s*CONNECTOR(?:\s*\(6\+2\))?|PCIE\s*(?:6\+2|8)-?PIN|(?:6\+2|8\s*\(6\+2\))\s*PIN\s*PCIE"

    for pattern in count_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    if re.search(presence_pattern, text, re.IGNORECASE):
        return 1

    return None


def _compat_cpu_generations(raw: str) -> list[str]:
    if not raw or _is_na(raw):
        return []

    generations: list[str] = []
    text = raw.upper()

    for match in re.finditer(r"RYZEN\s+(\d{4})", text):
        token = f"Ryzen {match.group(1)}"
        if token not in generations:
            generations.append(token)

    for match in re.finditer(r"(\d{1,2})(?:ST|ND|RD|TH)?\s+GEN", text):
        token = f"Intel {match.group(1)}th Gen"
        if token not in generations:
            generations.append(token)

    for match in re.finditer(r"CORE\s+ULTRA.*?SERIES\s*(\d+)", text):
        token = f"Core Ultra Series {match.group(1)}"
        if token not in generations:
            generations.append(token)

    return generations


def _compat_memory_slots(raw: str) -> Optional[int]:
    if not raw or _is_na(raw):
        return None

    patterns = [
        r"(\d+)\s*[xX]\s*(?:DDR\d|DIMM|SO-?DIMM|288-PIN|260-PIN)",
        r"(\d+)\s*(?:DIMM|SO-?DIMM)\s*SLOTS?",
        r"(\d+)\s*SLOTS?",
    ]
    for pattern in patterns:
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _compat_storage_connectivity(raw: str) -> tuple[Optional[int], Optional[int]]:
    if not raw or _is_na(raw):
        return None, None

    m2_slots: Optional[int] = None
    sata_ports: Optional[int] = None

    for pattern in (r"(\d+)\s*[xX]\s*M\.?2", r"M\.?2\s*(?:SLOTS?)?\s*(\d+)"):
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            m2_slots = int(match.group(1))
            break

    for pattern in (r"(\d+)\s*[xX]\s*SATA", r"(\d+)\s*SATA(?:\s*6GB/S)?"):
        match = re.search(pattern, raw, re.IGNORECASE)
        if match:
            sata_ports = int(match.group(1))
            break

    return m2_slots, sata_ports


def _compat_dimm_type(raw: str, name: str) -> str:
    text = f"{raw} {name}".upper()
    if "SO-DIMM" in text or "SODIMM" in text or "LAPTOP" in text:
        return "SO-DIMM"
    if "UDIMM" in text:
        return "UDIMM"
    if "RDIMM" in text or "REGISTERED" in text:
        return "RDIMM"
    if "DIMM" in text or "DESKTOP" in text:
        return "DIMM"
    return ""


def _compat_psu_form_factor(raw: str, name: str) -> str:
    text = f"{raw} {name}".upper()
    for form_factor in ("SFX-L", "SFX", "TFX", "ATX"):
        if form_factor in text:
            return form_factor
    return ""


def _compat_radiator_sizes(*values: str) -> list[int]:
    standards = [420, 360, 280, 240, 140, 120]
    found: list[int] = []

    for raw in values:
        if not raw or _is_na(raw):
            continue
        text = raw.upper()
        for standard in standards:
            if re.search(fr"\b{standard}\s*MM\b", text) and standard not in found:
                found.append(standard)

        if not found:
            dims = _compat_dimensions_mm(raw)
            if dims:
                longest = max(dims)
                nearest = min(standards, key=lambda size: abs(size - longest))
                if abs(nearest - longest) <= 50 and nearest not in found:
                    found.append(nearest)

    return found


def _compat_drive_bays(raw: str) -> tuple[Optional[int], Optional[int]]:
    if not raw or _is_na(raw):
        return None, None

    text = raw.upper().replace("”", "\"").replace("″", "\"")
    hdd_bays: Optional[int] = None
    ssd_bays: Optional[int] = None

    for pattern in (r"(\d+)\s*[xX]\s*3\.5", r"(\d+)[^0-9]{0,12}3\.5[^0-9]{0,12}HDD"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hdd_bays = int(match.group(1))
            break

    for pattern in (r"(\d+)\s*[xX]\s*2\.5", r"(\d+)[^0-9]{0,12}2\.5[^0-9]{0,12}SSD"):
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ssd_bays = int(match.group(1))
            break

    return hdd_bays, ssd_bays

def extract_processor(doc: dict) -> dict:
    raw_socket = _spec(doc, "Socket", "socket", "CPU Socket", "Processor Socket Type")
    raw_tdp = _spec(doc, "Default TDP", "TDP", "Thermal Design Power", "Max TDP", "Power")
    raw_ddr = _spec(doc, "Memory Support", "Memory Types", "Memory Type", "Supported Memory Type")
    
    name = doc.get("name", "")
    socket = _socket(raw_socket) or _infer_socket_from_name(name)
    tdp = _tdp_watts(raw_tdp)
    ddr_type = _ddr_type(raw_ddr)
    
    return {
        "socket": socket,
        "cores_total": None,
        "cores_performance": None,
        "cores_efficiency": None,
        "threads": None,
        "base_clock_mhz": None,
        "boost_clock_mhz": None,
        "tdp_w": tdp,
        "max_tdp_w": None,
        "l3_cache_mb": None,
        "memory_type": ddr_type,
        "max_memory_speed_mhz": None,
        "max_memory_channels": None,
        "has_igpu": None,
        "igpu_model": None,
        "unlocked": None,
        "pcie_version": None,
        "manufacturing_nm": None,
        "platform": None,
        "series": None,
        "architecture": None,
    }

def extract_motherboard(doc: dict) -> dict:
    raw_socket = _spec(doc, "Socket", "socket", "CPU Socket", "Motherboard Socket")
    raw_cpu = _spec(doc, "CPU", "Cpu Type", "CPU Support", "Compatible CPUs", "Supported Processors")
    raw_memory = _spec(doc, "Memory", "RAM", "Supported Memory Type", "RAM Type", "Memory Type")
    raw_max_ram = _spec(doc, "Motherboard Max RAM Support", "Max Memory Support", "Max Memory", "Maximum Memory", "Max RAM")
    raw_speed = _spec(doc, "Memory Speed", "Max Memory Speed", "Supported Memory Speed")
    raw_form = _spec(doc, "Form Factor", "Motherboard Form Factor", "Board Type")
    raw_pcie = _spec(doc, "Expansion Slots", "PCIe Slots", "Slots")
    raw_slots = _spec(doc, "Memory Slots", "DIMM Slots", "RAM Slots")
    raw_storage = _spec(doc, "Storage", "Storage Interface")

    name = doc.get("name", "")
    socket = _socket(raw_socket)
    ddr_type = _ddr_type(raw_memory or name)
    max_ram_gb = _gb(raw_max_ram or raw_memory)
    max_ram_speed_mhz = _speed_mhz(raw_speed or raw_memory)
    form_factors = _form_factor_list(raw_form or name)
    
    ram_slots = None
    if raw_slots and not _is_na(raw_slots):
        m = re.search(r"\d+", raw_slots)
        if m: ram_slots = int(m.group())

    pcie_x16_slots = 1
    if raw_pcie and not _is_na(raw_pcie):
        slot_text = raw_pcie.upper().replace("×", "X")
        count = sum(int(match.group(1)) for match in re.finditer(r"(\d+)\s*[xX]\s*(?:PCI(?:E| EXPRESS)[^,\n;:]*)?[xX]\s*16", slot_text, re.IGNORECASE))
        if count: pcie_x16_slots = count
        
    m2_slots = None
    sata_ports = None

    return {
        "socket": socket,
        "chipset": None,
        "platform": None,
        "form_factor": form_factors[0] if form_factors else None,
        "memory_type": ddr_type,
        "memory_slots": ram_slots,
        "max_memory_gb": max_ram_gb,
        "max_memory_speed_mhz": max_ram_speed_mhz,
        "pcie_version": None,
        "m2_slots": m2_slots,
        "sata_ports": sata_ports,
        "has_wifi": None,
        "wifi_standard": None,
        "has_bluetooth": None,
        "usb_rear_json": None,
        "audio_codec": None,
        "lan_speed_gbps": None,
        "supports_ecc": None,
    }

def extract_ram(doc: dict) -> dict:
    raw_cap = _spec(doc, "Capacity", "RAM Capacity", "Total Capacity", "Memory Size", "Size", "Module Size")
    raw_type = _spec(doc, "Memory Type", "RAM Type", "Type", "Memory Technology")
    raw_speed = _spec(doc, "RAM Speed", "Tested Speed", "Speed", "Memory Speed", "Frequency", "Clock Speed")
    raw_kit = _spec(doc, "RAM Channel Kit", "Kit Type", "Kit", "Number of Modules", "Configuration", "Module Configuration")
    raw_latency = _spec(doc, "Tested Latency", "CAS Latency", "CL", "Latency", "CAS")
    raw_voltage = _spec(doc, "Tested Voltage", "Voltage", "Operating Voltage")
    raw_dimm = _spec(doc, "Package Memory Format", "Module Type", "Dimm Type", "DIMM Type", "Form Factor", "Memory Suitable For")

    name = doc.get("name") or ""
    
    modules = None
    for source in (raw_kit, raw_cap, name):
        if not source: continue
        match = re.search(r"(\d+)\s*[xX]\s*\d+\s*GB", source, re.IGNORECASE)
        if match:
            modules = int(match.group(1))
            break
        match = re.search(r"\((\d+)\s*GB\s*[xX]\s*(\d+)\)", source, re.IGNORECASE)
        if match:
            modules = int(match.group(2))
            break

    cas = None
    if raw_latency and not _is_na(raw_latency):
        m = re.search(r"\b(\d{1,2})\b", raw_latency)
        if m: cas = int(m.group(1))
        
    voltage = None
    if raw_voltage and not _is_na(raw_voltage):
        m = re.search(r"([\d.]+)\s*V", raw_voltage, re.IGNORECASE)
        if m: voltage = float(m.group(1))

    return {
        "capacity_gb": _gb(raw_cap or name),
        "speed_mhz": _speed_mhz(raw_speed or name),
        "type": _ddr_type(raw_type or name),
        "kit_count": modules,
        "cas_latency": cas,
        "voltage_v": voltage,
        "has_xmp": None,
        "has_expo": None,
        "form_factor": raw_dimm.upper() if raw_dimm else None,
        "has_rgb": None,
    }

def extract_psu(doc: dict) -> dict:
    raw_watt = _spec(doc, "Wattage", "Power Output", "Capacity", "Max Power", "Continuous Power", "Power", "SMPS Watt", "Continuous power W", "Output Capacity")
    name = doc.get("name") or ""
    raw_eff = _spec(doc, "Efficiency", "80 Plus", "Efficiency Rating", "Certificate", "80+", "Rating", "Certification")
    raw_mod = _spec(doc, "Modular", "Cable Management", "Modularity", "Modular Cables")
    raw_form = _spec(doc, "PSU Form Factor", "Form Factor", "Type")

    return {
        "wattage_w": _psu_watts(raw_watt or name),
        "efficiency_rating": _efficiency_tier(raw_eff, name),
        "modularity": _modular(raw_mod, name),
        "form_factor": raw_form,
        "pcie_connectors": None,
        "atx12v_connectors": None,
        "sata_connectors": None,
        "fan_size_mm": None,
        "mtbf_hours": None,
    }

def extract_storage(doc: dict) -> dict:
    raw_cat = _spec(doc, "Category", "Type", "Drive Type", "Storage Type")
    raw_form = _spec(doc, "Form Factor", "Drive Form Factor")
    raw_cap = _spec(doc, "Capacity", "Storage Capacity", "Size")
    raw_iface = _spec(doc, "Interface", "Connection", "Bus")
    raw_nvme = _spec(doc, "NVMe", "NVMe Support", "NVMe PCIe")

    name = doc.get("name") or ""
    combined_type = f"{raw_cat} {name}".upper()
    drive_type = ""
    if "SSD" in combined_type or "NVME" in combined_type: drive_type = "SSD"
    elif "HDD" in combined_type or "HARD DISK" in combined_type: drive_type = "HDD"

    combined_interface = f"{raw_iface} {raw_nvme} {name}".upper()
    interface = ""
    if "NVME" in combined_interface or "PCIE" in combined_interface or re.search(r"\bGEN[345]\b", combined_interface):
        interface = "NVMe"
    elif "SATA" in combined_interface: interface = "SATA"

    form_factor = _form_factor_list(raw_form or name)

    return {
        "type": drive_type,
        "form_factor": form_factor[0] if form_factor else None,
        "interface": interface,
        "capacity_gb": _gb(raw_cap),
        "seq_read_mbps": None,
        "seq_write_mbps": None,
        "rand_read_iops": None,
        "rand_write_iops": None,
        "tbw": None,
        "nand_type": None,
        "has_dram_cache": None,
    }

def extract_cabinet(doc: dict) -> dict:
    raw_mobo = _spec(doc, "Motherboard Support", "Motherboard Size", "Compatible Motherboards", "Supported Form Factors")
    raw_gpu = _spec(doc, "Maximum GPU Length", "Max GPU Length", "Maximum Graphics Card Length", "Max Graphics Card Length")
    raw_cooler = _spec(doc, "Maximum CPU Cooler Height", "Max CPU Cooler Height", "CPU Cooler Height", "Max Cooler Height")
    raw_psu = _spec(doc, "Maximum PSU Length", "Max PSU Length")
    raw_exp = _spec(doc, "Expansion Slots")
    
    exp_slots = None
    if raw_exp and not _is_na(raw_exp):
        m = re.search(r"\d+", raw_exp)
        if m: exp_slots = int(m.group())

    return {
        "form_factor_support": _form_factor_list(raw_mobo or doc.get("name", "")),
        "max_gpu_length_mm": _mm(raw_gpu),
        "max_cpu_cooler_height_mm": _mm(raw_cooler),
        "max_psu_length_mm": _mm(raw_psu),
        "expansion_slots": exp_slots,
        "drive_bays_25": None,
        "drive_bays_35": None,
        "front_usb_ports_json": None,
        "has_type_c_front": None,
        "radiator_support_front_mm": None,
        "radiator_support_top_mm": None,
        "has_tempered_glass": None,
        "has_rgb": None,
        "material": None,
        "color": None,
    }

def extract_cooler(doc: dict) -> dict:
    raw_type = _spec(doc, "Cooling Type", "Type", "Cooler Type")
    raw_tdp = _spec(doc, "TDP", "Max TDP", "Heat Dissipation", "Cooling Capacity", "Max CPU TDP")
    raw_sockets = _spec(doc, "Socket Support", "Compatible Sockets", "Supported Sockets", "CPU Socket", "Socket Compatibility", "Socket", "Compatibility")
    
    name = doc.get("name", "")
    cooler_text = f"{raw_type} {name}".upper()
    cooler_type = "Air"
    if any(token in cooler_text for token in ("LIQUID", "AIO", "WATER", "KRAKEN")):
        cooler_type = "AIO"
        
    return {
        "type": cooler_type,
        "radiator_size_mm": None,
        "fan_speed_max_rpm": None,
        "noise_level_max_dba": None,
        "tdp_rating_w": _tdp_watts(raw_tdp),
        "socket_support": _socket_list(raw_sockets),
        "has_argb": None,
        "fan_dimensions_mm": None,
        "height_mm": None,
    }

EXTRACTORS: dict[str, Any] = {
    "Processors":   extract_processor,
    "Motherboards": extract_motherboard,
    "RAM":          extract_ram,
    "GPUs":         extract_gpu,
    "SMPS":         extract_psu,
    "CpuCoolers":   extract_cooler,
    "Cabinets":     extract_cabinet,
    "Storage":      extract_storage,
}


def extract_features(collection_name: str, doc: dict) -> dict:
    features = EXTRACTORS[collection_name](doc)
    features.update({
        "_source_id":         str(doc["_id"]),
        "_source_collection": collection_name,
        "name":               doc.get("name") or doc.get("title") or "",
        "source_retailer":    doc.get("source", ""),
        "price":              _price_number(doc),
        "in_stock":           doc.get("out_of_stock") is not True,
        "extracted_at":       datetime.now(timezone.utc).isoformat(),
    })
    return features


# ─────────────────────────────────────────────────────────────────────
#  QUALITY REPORTER
# ─────────────────────────────────────────────────────────────────────

_META_FIELDS = {
    "_source_id", "_source_collection", "name", "source_retailer",
    "price", "in_stock", "extracted_at", "component_type",
}


def quality_report(collection_name: str, results: list[dict]) -> dict:
    if not results:
        log.warning("[%s] No results — skipping quality report", collection_name)
        return {}

    field_names = sorted({k for r in results for k in r if k not in _META_FIELDS})
    total       = len(results)
    report: dict[str, Any] = {"total_docs": total, "fields": {}}

    log.info("─" * 66)
    log.info("Quality  %-22s  %d documents", collection_name, total)
    log.info("─" * 66)

    for field in field_names:
        filled = sum(1 for r in results if r.get(field) not in (None, "", [], 0, False))
        pct    = filled / total * 100
        bar    = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        flag   = "⚠ " if pct < 30 else "  "
        log.info("%s %-28s %s %3.0f%%  (%d/%d)", flag, field, bar, pct, filled, total)
        report["fields"][field] = {
            "fill_rate_pct": round(pct, 1),
            "filled": filled,
            "total":  total,
        }

    log.info("─" * 66)
    return report


# ─────────────────────────────────────────────────────────────────────
#  OUTPUT WRITER
# ─────────────────────────────────────────────────────────────────────

def write_outputs(
    collection_name: str,
    results: list[dict],
    quality: dict,
    failed_docs: list[dict],
    source_docs: Optional[list[dict]] = None,
) -> None:
    out_dir = os.path.join(OUTPUT_DIR, collection_name)
    os.makedirs(out_dir, exist_ok=True)

    with open(os.path.join(out_dir, "features.json"), "w", encoding="utf-8") as f:
        f.write(_dump(results))
    log.info("[%s] features.json — %d records → %s", collection_name, len(results), out_dir)

    with open(os.path.join(out_dir, "quality.json"), "w", encoding="utf-8") as f:
        f.write(_dump(quality))

    if failed_docs:
        with open(os.path.join(out_dir, "failed.json"), "w", encoding="utf-8") as f:
            f.write(_dump(failed_docs))
    if source_docs is not None:
        with open(os.path.join(out_dir, "source_docs.json"), "w", encoding="utf-8") as f:
            f.write(_dump(source_docs))
        log.info("[%s] source_docs.json -> %d records in %s", collection_name, len(source_docs), out_dir)
        log.warning("[%s] %d failures → failed.json", collection_name, len(failed_docs))


# ─────────────────────────────────────────────────────────────────────
    if source_docs is not None:
        with open(os.path.join(out_dir, "source_docs.json"), "w", encoding="utf-8") as f:
            f.write(_dump(source_docs))
        log.info("[%s] source_docs.json â€” %d records â†’ %s", collection_name, len(source_docs), out_dir)

    source_docs = None

#  PIPELINE RUNNER
# ─────────────────────────────────────────────────────────────────────

    if source_docs is not None:
        with open(os.path.join(out_dir, "source_docs.json"), "w", encoding="utf-8") as f:
            f.write(_dump(source_docs))
        log.info("[%s] source_docs.json â€” %d records â†’ %s", collection_name, len(source_docs), out_dir)


def run_collection(
    db,
    collection_name: str,
    verbose: bool,
    dump_source_docs: bool,
) -> tuple[int, int, int]:
    coll  = db[collection_name]
    total = coll.count_documents({})

    if total == 0:
        log.warning("[%s] Empty — skipping", collection_name)
        return 0, 0, 0

    log.info("══ %s  (%d docs) ══", collection_name, total)

    results:     list[dict] = []
    failed_docs: list[dict] = []
    source_docs: Optional[list[dict]] = [] if dump_source_docs else None

    for doc in coll.find({}):
        if source_docs is not None:
            source_docs.append(doc)
        try:
            features = extract_features(collection_name, doc)
            results.append(features)
            if verbose:
                compat = {k: v for k, v in features.items() if k not in _META_FIELDS}
                log.debug("  %s\n      → %s", features["name"][:60], compat)
        except Exception as exc:
            failed_docs.append({
                "_id":   str(doc.get("_id", "")),
                "name":  doc.get("name", ""),
                "error": str(exc),
            })
            log.warning("  FAIL %s : %s", doc.get("_id"), exc)

    quality = quality_report(collection_name, results)
    write_outputs(collection_name, results, quality, failed_docs, source_docs)
    return total, len(results), len(failed_docs)


def run_pipeline(only_collection: Optional[str], verbose: bool, dump_source_docs: bool) -> None:
    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    collections = [only_collection] if only_collection else SOURCE_COLLECTIONS
    grand_total = grand_ok = grand_failed = 0
    summary: dict = {}

    for name in collections:
        if name not in EXTRACTORS:
            log.error("No extractor for '%s'. Valid: %s", name, list(EXTRACTORS))
            continue
        total, ok, failed = run_collection(db, name, verbose, dump_source_docs)
        grand_total  += total
        grand_ok     += ok
        grand_failed += failed
        summary[name] = {"total": total, "ok": ok, "failed": failed}

    with open(os.path.join(OUTPUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
        f.write(_dump({
            "ran_at":       datetime.now(timezone.utc).isoformat(),
            "grand_total":  grand_total,
            "grand_ok":     grand_ok,
            "grand_failed": grand_failed,
            "collections":  summary,
        }))

    log.info("═" * 66)
    log.info("DONE  total=%d  ok=%d  failed=%d", grand_total, grand_ok, grand_failed)
    log.info("Output → %s", OUTPUT_DIR)
    log.info("═" * 66)
    client.close()


# ─────────────────────────────────────────────────────────────────────
#  ENTRYPOINT
# ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract compatibility features from PC components → JSON files."
    )
    parser.add_argument(
        "--collection", type=str, default=None, metavar="NAME",
        help=f"Run only one collection. Options: {SOURCE_COLLECTIONS}",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print extracted features for every document.",
    )
    parser.add_argument(
        "--dump-source-docs", action="store_true",
        help="Also export the raw MongoDB documents used for extraction.",
    )
    args = parser.parse_args()
    run_pipeline(
        only_collection=args.collection,
        verbose=args.verbose,
        dump_source_docs=args.dump_source_docs,
    )




if __name__ == '__main__':
    main()
