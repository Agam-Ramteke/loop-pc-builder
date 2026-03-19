from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www.techpowerup.com"
INDEX_URL = f"{BASE_URL}/gpu-specs/"
DEFAULT_JSON_OUTPUT = Path("gpu_specs.json")
DEFAULT_TIMEOUT_SECONDS = 30

USER_AGENTS = [
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/132.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/18.1 Safari/605.1.15"
    ),
    (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) "
        "Gecko/20100101 Firefox/133.0"
    ),
]

EXCLUDED_NAME_PATTERNS = [
    r"\bmobile\b",
    r"max-?q",
    r"quadro",
    r"\btesla\b",
    r"\binstinct\b",
    r"radeon pro",
    r"\brtx a\d",
    r"laptop gpu",
    r"\biris\b",
    r"\bhd graphics\b",
    r"\buhd graphics\b",
    r"\bintegrated\b",
    r"\bworkstation\b",
    r"\bdatacenter\b",
    r"\bprototype\b",
    r"\bunreleased\b",
    r"\bengineering sample\b",
]

LINK_PATTERN = re.compile(r"/gpu-specs/[^?#]+\.c\d+/?$")
BOT_CHALLENGE_MARKERS = (
    "Automated bot check in progress",
    "/.firewall/verify",
    'id="pow-progress-bar"',
    "var TOKEN =",
)

FIELD_ALIASES: dict[str, list[str]] = {
    "architecture": ["Architecture"],
    "release_date": ["Release Date", "Launch Date", "Released"],
    "process_node": ["Process Size", "Process Node", "Manufacturing Process"],
    "die_size": ["Die Size"],
    "transistor_count": ["Transistors", "Transistor Count"],
    "generation": ["Generation"],
    "predecessor": ["Predecessor"],
    "successor": ["Successor"],
    "gpu_chip": ["GPU Chip", "Graphics Processor", "GPU Name", "Chip"],
    "cuda_cores_shaders": [
        "CUDA Cores",
        "CUDA Core",
        "Shaders",
        "Shader Units",
        "Shading Units",
        "Stream Processors",
    ],
    "tensor_cores": ["Tensor Cores", "Tensor Units", "AI Accelerators"],
    "rt_cores": ["RT Cores", "Ray Accelerators", "Ray Tracing Cores"],
    "rops": ["ROPs", "Render Output Units"],
    "tmus": ["TMUs", "Texture Mapping Units"],
    "l1_cache": ["L1 Cache"],
    "l2_cache": ["L2 Cache"],
    "base_clock": ["Base Clock", "GPU Clock", "Core Clock"],
    "boost_clock": ["Boost Clock", "Boost", "Turbo Clock"],
    "memory_clock": ["Memory Clock", "Memory Speed"],
    "memory_size": ["Memory Size"],
    "memory_type": ["Memory Type"],
    "memory_bus_width": ["Memory Bus", "Memory Bus Width"],
    "memory_bandwidth": ["Bandwidth", "Memory Bandwidth"],
    "tdp": ["TDP", "Board Power", "Typical Board Power"],
    "recommended_psu": ["Suggested PSU", "Recommended PSU", "System Suggestion"],
    "power_connectors": ["Power Connectors", "External Power"],
    "slot_width": ["Slot Width"],
    "length_mm": ["Length", "Board Length"],
    "width_mm": ["Width", "Board Width"],
    "directx_support": ["DirectX", "DirectX Support"],
    "opengl_support": ["OpenGL", "OpenGL Support"],
    "vulkan_support": ["Vulkan", "Vulkan Support"],
    "shader_model": ["Shader Model"],
    "relative_performance_score": ["Relative Performance"],
}

CSV_FIELDS = [
    "gpu_name",
    "manufacturer",
    "architecture",
    "release_date",
    "process_node",
    "die_size",
    "transistor_count",
    "generation",
    "predecessor",
    "successor",
    "gpu_chip",
    "cuda_cores_shaders",
    "tensor_cores",
    "rt_cores",
    "rops",
    "tmus",
    "l1_cache",
    "l2_cache",
    "base_clock",
    "boost_clock",
    "memory_clock",
    "memory_size",
    "memory_type",
    "memory_bus_width",
    "memory_bandwidth",
    "tdp",
    "recommended_psu",
    "power_connectors",
    "slot_width",
    "length_mm",
    "width_mm",
    "directx_support",
    "opengl_support",
    "vulkan_support",
    "shader_model",
    "relative_performance_score",
    "specifications_json",
    "specification_sections_json",
    "source_url",
    "scraped_at",
]


class BotProtectionError(RuntimeError):
    """Raised when TechPowerUp serves the JavaScript bot challenge page."""


@dataclass(frozen=True)
class GpuEntry:
    gpu_name: str
    url: str


class RateLimiter:
    def __init__(self, min_delay: float, max_delay: float) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._first_request = True

    def wait(self) -> None:
        if self._first_request:
            self._first_request = False
            return

        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)


def configure_logging(verbose: bool) -> logging.Logger:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("techpowerup_gpu_scraper")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape consumer desktop GPU specs from TechPowerUp using "
            "requests + BeautifulSoup."
        )
    )
    parser.add_argument("--index-url", default=INDEX_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=None,
        help="Optional CSV export path.",
    )
    parser.add_argument(
        "--cookie-header",
        default=None,
        help=(
            "Optional raw Cookie header copied from a permitted browser session. "
            "Useful when TechPowerUp requires a JavaScript-validated session."
        ),
    )
    parser.add_argument("--min-delay", type=float, default=2.0)
    parser.add_argument("--max-delay", type=float, default=5.0)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from an existing JSON output file if present.",
    )
    parser.add_argument(
        "--include-raw-specs",
        action="store_true",
        help=(
            "Also include section-grouped raw specs in addition to the default "
            "flat specifications map."
        ),
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def build_session(cookie_header: str | None) -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Upgrade-Insecure-Requests": "1",
        }
    )

    if cookie_header:
        for chunk in cookie_header.split(";"):
            if "=" not in chunk:
                continue
            name, value = chunk.split("=", 1)
            session.cookies.set(
                name=name.strip(),
                value=value.strip(),
                domain="www.techpowerup.com",
            )

    return session


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()
    return cleaned or None


def random_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": INDEX_URL,
    }


def is_bot_challenge(html: str) -> bool:
    lowered = html.lower()
    return any(marker.lower() in lowered for marker in BOT_CHALLENGE_MARKERS)


def fetch_html(
    session: requests.Session,
    url: str,
    *,
    timeout: int,
    rate_limiter: RateLimiter,
    logger: logging.Logger,
) -> str:
    rate_limiter.wait()
    response = session.get(url, headers=random_headers(), timeout=timeout)
    response.raise_for_status()

    if is_bot_challenge(response.text):
        raise BotProtectionError(
            "TechPowerUp returned a JavaScript bot-check page instead of the "
            f"requested content for {url}. Supply a valid browser session via "
            "--cookie-header if you have permission to scrape this site."
        )

    logger.debug("Fetched %s (%s)", url, response.status_code)
    return response.text


def log_robots_notice(
    session: requests.Session,
    *,
    timeout: int,
    logger: logging.Logger,
) -> None:
    try:
        response = session.get(f"{BASE_URL}/robots.txt", timeout=timeout, headers=random_headers())
        response.raise_for_status()
    except requests.RequestException:
        return

    body = response.text.lower()
    if "scrape" in body or "data mine" in body:
        logger.warning(
            "TechPowerUp robots.txt includes anti-scraping language. Make sure you "
            "have permission before running this scraper at scale."
        )


def load_existing_records(output_path: Path) -> list[dict[str, Any]]:
    if not output_path.exists():
        return []

    with output_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, list):
        raise ValueError(f"{output_path} does not contain a JSON array.")

    return [item for item in payload if isinstance(item, dict)]


def save_json(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2, ensure_ascii=False)


def save_csv(records: list[dict[str, Any]], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(build_csv_row(record))


def slug_to_name(url: str) -> str:
    slug = Path(urlparse(url).path).name
    slug = re.sub(r"\.c\d+$", "", slug)
    words = [part for part in slug.split("-") if part]
    return " ".join(word.upper() if word.isdigit() else word.capitalize() for word in words)


def parse_index_entries(html: str) -> list[GpuEntry]:
    soup = BeautifulSoup(html, "html.parser")
    entries: dict[str, GpuEntry] = {}

    for anchor in soup.select('a[href*="/gpu-specs/"]'):
        href = clean_text(anchor.get("href"))
        if not href:
            continue

        absolute_url = urljoin(INDEX_URL, href)
        path = urlparse(absolute_url).path
        if not LINK_PATTERN.search(path):
            continue

        gpu_name = clean_text(anchor.get_text(" ", strip=True)) or slug_to_name(absolute_url)
        entries.setdefault(absolute_url, GpuEntry(gpu_name=gpu_name, url=absolute_url))

    return sorted(entries.values(), key=lambda item: item.gpu_name.casefold())


def extract_spec_fields(soup: BeautifulSoup) -> dict[str, str]:
    fields: dict[str, str] = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) < 2:
                continue

            label = clean_text(cells[0].get_text(" ", strip=True))
            value = clean_text(" ".join(cell.get_text(" ", strip=True) for cell in cells[1:]))
            if label and value and label not in fields:
                fields[label] = value

    for definition_list in soup.find_all("dl"):
        terms = definition_list.find_all("dt")
        descriptions = definition_list.find_all("dd")
        for label_node, value_node in zip(terms, descriptions):
            label = clean_text(label_node.get_text(" ", strip=True))
            value = clean_text(value_node.get_text(" ", strip=True))
            if label and value and label not in fields:
                fields[label] = value

    for item in soup.find_all("li"):
        text = clean_text(item.get_text(" ", strip=True))
        if not text or ":" not in text:
            continue
        label, value = text.split(":", 1)
        label = clean_text(label)
        value = clean_text(value)
        if label and value and label not in fields:
            fields[label] = value

    return fields


def merge_section_fields(
    target: dict[str, dict[str, str]],
    section_name: str,
    rows: dict[str, str],
) -> None:
    section = target.setdefault(section_name, {})
    for label, value in rows.items():
        section.setdefault(label, value)


def get_section_name(node: Any, fallback_index: int) -> str:
    caption = getattr(node, "find", lambda *args, **kwargs: None)("caption")
    caption_text = clean_text(caption.get_text(" ", strip=True)) if caption else None
    if caption_text:
        return caption_text

    heading = node.find_previous(["h2", "h3", "h4", "legend"])
    heading_text = clean_text(heading.get_text(" ", strip=True)) if heading else None
    if heading_text:
        return heading_text

    return f"section_{fallback_index}"


def extract_spec_sections(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    section_index = 1

    for table in soup.find_all("table"):
        rows: dict[str, str] = {}
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) < 2:
                continue

            label = clean_text(cells[0].get_text(" ", strip=True))
            value = clean_text(" ".join(cell.get_text(" ", strip=True) for cell in cells[1:]))
            if label and value:
                rows.setdefault(label, value)

        if rows:
            merge_section_fields(sections, get_section_name(table, section_index), rows)
            section_index += 1

    for definition_list in soup.find_all("dl"):
        rows: dict[str, str] = {}
        terms = definition_list.find_all("dt")
        descriptions = definition_list.find_all("dd")
        for label_node, value_node in zip(terms, descriptions):
            label = clean_text(label_node.get_text(" ", strip=True))
            value = clean_text(value_node.get_text(" ", strip=True))
            if label and value:
                rows.setdefault(label, value)

        if rows:
            merge_section_fields(sections, get_section_name(definition_list, section_index), rows)
            section_index += 1

    return sections


def get_first_matching_field(fields: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        for key, value in fields.items():
            if key.casefold() == alias.casefold():
                return value
    return None


def parse_ordinal_date(value: str | None) -> str | None:
    text = clean_text(value)
    if not text:
        return None

    normalized = re.sub(r"(\d{1,2})(st|nd|rd|th)", r"\1", text, flags=re.IGNORECASE)
    formats = (
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %Y",
        "%B %Y",
        "%Y-%m-%d",
        "%Y",
    )

    for fmt in formats:
        try:
            parsed = datetime.strptime(normalized, fmt)
        except ValueError:
            continue

        if fmt == "%Y":
            return parsed.strftime("%Y")
        if fmt in {"%b %Y", "%B %Y"}:
            return parsed.strftime("%Y-%m")
        return parsed.date().isoformat()

    return text


def extract_first_number(value: str | None, *, allow_decimal: bool = False) -> int | float | None:
    text = clean_text(value)
    if not text:
        return None

    pattern = r"[-+]?\d+(?:\.\d+)?" if allow_decimal else r"[-+]?\d+"
    match = re.search(pattern, text.replace(",", ""))
    if not match:
        return None

    if allow_decimal:
        return float(match.group())
    return int(match.group())


def extract_dimension_mm(value: str | None) -> int | None:
    text = clean_text(value)
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*mm", text, flags=re.IGNORECASE)
    if match:
        return int(round(float(match.group(1))))

    number = extract_first_number(text)
    return int(number) if isinstance(number, int) else None


def extract_percentage(value: str | None) -> float | None:
    text = clean_text(value)
    if not text:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if match:
        return float(match.group(1))
    return None


def split_combined_counts(value: str | None) -> tuple[int | None, int | None, int | None]:
    text = clean_text(value)
    if not text:
        return None, None, None

    parts = [part.strip() for part in re.split(r"/|\|", text)]
    if len(parts) < 3:
        return None, None, None

    parsed = [extract_first_number(part) for part in parts[:3]]
    return (
        int(parsed[0]) if isinstance(parsed[0], int) else None,
        int(parsed[1]) if isinstance(parsed[1], int) else None,
        int(parsed[2]) if isinstance(parsed[2], int) else None,
    )


def detect_manufacturer(gpu_name: str | None, fields: dict[str, str]) -> str | None:
    haystack = " ".join(
        filter(
            None,
            [
                gpu_name or "",
                fields.get("Vendor", ""),
                fields.get("Architecture", ""),
                fields.get("Generation", ""),
            ],
        )
    ).casefold()

    if any(token in haystack for token in ("nvidia", "geforce", "gtx", "rtx", "titan")):
        return "NVIDIA"
    if any(token in haystack for token in ("amd", "radeon", "rx ", "rx-", "vega", "firepro")):
        return "AMD"
    if any(token in haystack for token in ("intel", "arc")):
        return "Intel"
    return None


def parse_relative_performance(soup: BeautifulSoup, fields: dict[str, str]) -> float | None:
    field_value = get_first_matching_field(fields, FIELD_ALIASES["relative_performance_score"])
    if field_value:
        parsed = extract_percentage(field_value)
        if parsed is not None:
            return parsed

    for text in soup.stripped_strings:
        cleaned = clean_text(text)
        if not cleaned or "relative performance" not in cleaned.casefold():
            continue
        parsed = extract_percentage(cleaned)
        if parsed is not None:
            return parsed

    return None


def should_exclude_by_name(gpu_name: str | None) -> bool:
    if not gpu_name:
        return True

    lowered = gpu_name.casefold()
    return any(re.search(pattern, lowered, flags=re.IGNORECASE) for pattern in EXCLUDED_NAME_PATTERNS)


def is_future_or_unreleased(release_date: str | None) -> bool:
    text = clean_text(release_date)
    if not text:
        return False

    lowered = text.casefold()
    if any(token in lowered for token in ("unreleased", "announced", "paper launch", "prototype")):
        return True

    iso_match = re.fullmatch(r"\d{4}-\d{2}-\d{2}", text)
    if iso_match:
        try:
            return date.fromisoformat(text) > date.today()
        except ValueError:
            return False

    year_month_match = re.fullmatch(r"\d{4}-\d{2}", text)
    if year_month_match:
        year, month = [int(part) for part in text.split("-")]
        try:
            candidate = date(year, month, 1)
        except ValueError:
            return False
        return candidate > date.today().replace(day=1)

    year_match = re.fullmatch(r"\d{4}", text)
    if year_match:
        return int(text) > date.today().year

    return False


def build_record(
    soup: BeautifulSoup,
    url: str,
    fallback_name: str,
    *,
    include_raw_specs: bool,
) -> dict[str, Any]:
    raw_fields = extract_spec_fields(soup)
    specification_sections = extract_spec_sections(soup)

    page_name = None
    h1 = soup.find("h1")
    if h1:
        page_name = clean_text(h1.get_text(" ", strip=True))
    if not page_name:
        page_name = fallback_name

    combined_counts = get_first_matching_field(
        raw_fields,
        ["Shaders / TMUs / ROPs", "Shading Units / TMUs / ROPs"],
    )
    combined_shaders, combined_tmus, combined_rops = split_combined_counts(combined_counts)

    record: dict[str, Any] = {
        "gpu_name": page_name,
        "manufacturer": detect_manufacturer(page_name, raw_fields),
        "architecture": get_first_matching_field(raw_fields, FIELD_ALIASES["architecture"]),
        "release_date": parse_ordinal_date(
            get_first_matching_field(raw_fields, FIELD_ALIASES["release_date"])
        ),
        "process_node": get_first_matching_field(raw_fields, FIELD_ALIASES["process_node"]),
        "die_size": get_first_matching_field(raw_fields, FIELD_ALIASES["die_size"]),
        "transistor_count": get_first_matching_field(raw_fields, FIELD_ALIASES["transistor_count"]),
        "generation": get_first_matching_field(raw_fields, FIELD_ALIASES["generation"]),
        "predecessor": get_first_matching_field(raw_fields, FIELD_ALIASES["predecessor"]),
        "successor": get_first_matching_field(raw_fields, FIELD_ALIASES["successor"]),
        "gpu_chip": get_first_matching_field(raw_fields, FIELD_ALIASES["gpu_chip"]),
        "cuda_cores_shaders": (
            extract_first_number(
                get_first_matching_field(raw_fields, FIELD_ALIASES["cuda_cores_shaders"])
            )
            or combined_shaders
        ),
        "tensor_cores": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["tensor_cores"])
        ),
        "rt_cores": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["rt_cores"])
        ),
        "rops": (
            extract_first_number(get_first_matching_field(raw_fields, FIELD_ALIASES["rops"]))
            or combined_rops
        ),
        "tmus": (
            extract_first_number(get_first_matching_field(raw_fields, FIELD_ALIASES["tmus"]))
            or combined_tmus
        ),
        "l1_cache": get_first_matching_field(raw_fields, FIELD_ALIASES["l1_cache"]),
        "l2_cache": get_first_matching_field(raw_fields, FIELD_ALIASES["l2_cache"]),
        "base_clock": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["base_clock"])
        ),
        "boost_clock": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["boost_clock"])
        ),
        "memory_clock": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["memory_clock"])
        ),
        "memory_size": get_first_matching_field(raw_fields, FIELD_ALIASES["memory_size"]),
        "memory_type": get_first_matching_field(raw_fields, FIELD_ALIASES["memory_type"]),
        "memory_bus_width": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["memory_bus_width"])
        ),
        "memory_bandwidth": get_first_matching_field(raw_fields, FIELD_ALIASES["memory_bandwidth"]),
        "tdp": extract_first_number(get_first_matching_field(raw_fields, FIELD_ALIASES["tdp"])),
        "recommended_psu": extract_first_number(
            get_first_matching_field(raw_fields, FIELD_ALIASES["recommended_psu"])
        ),
        "power_connectors": get_first_matching_field(raw_fields, FIELD_ALIASES["power_connectors"]),
        "slot_width": get_first_matching_field(raw_fields, FIELD_ALIASES["slot_width"]),
        "length_mm": extract_dimension_mm(
            get_first_matching_field(raw_fields, FIELD_ALIASES["length_mm"])
        ),
        "width_mm": extract_dimension_mm(
            get_first_matching_field(raw_fields, FIELD_ALIASES["width_mm"])
        ),
        "directx_support": get_first_matching_field(raw_fields, FIELD_ALIASES["directx_support"]),
        "opengl_support": get_first_matching_field(raw_fields, FIELD_ALIASES["opengl_support"]),
        "vulkan_support": get_first_matching_field(raw_fields, FIELD_ALIASES["vulkan_support"]),
        "shader_model": get_first_matching_field(raw_fields, FIELD_ALIASES["shader_model"]),
        "relative_performance_score": parse_relative_performance(soup, raw_fields),
        "specifications": raw_fields,
        "source_url": url,
        "scraped_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
    }

    if include_raw_specs:
        record["specification_sections"] = specification_sections

    return record


def build_csv_row(record: dict[str, Any]) -> dict[str, Any]:
    row = dict(record)
    row["specifications_json"] = json.dumps(
        record.get("specifications", {}),
        ensure_ascii=False,
        sort_keys=True,
    )
    row["specification_sections_json"] = json.dumps(
        record.get("specification_sections", {}),
        ensure_ascii=False,
        sort_keys=True,
    )
    return row


def should_include_record(record: dict[str, Any]) -> tuple[bool, str | None]:
    gpu_name = clean_text(record.get("gpu_name"))
    if should_exclude_by_name(gpu_name):
        return False, "excluded name pattern"

    if is_future_or_unreleased(record.get("release_date")):
        return False, "future or unreleased GPU"

    manufacturer = clean_text(record.get("manufacturer"))
    if manufacturer not in {"NVIDIA", "AMD", "Intel"}:
        return False, "unsupported manufacturer"

    return True, None


def scrape_gpus(args: argparse.Namespace, logger: logging.Logger) -> int:
    session = build_session(args.cookie_header)
    rate_limiter = RateLimiter(args.min_delay, args.max_delay)

    log_robots_notice(session, timeout=args.timeout, logger=logger)

    records = load_existing_records(args.output) if args.resume else []
    processed_urls = {
        clean_text(record.get("source_url"))
        for record in records
        if isinstance(record, dict)
    }

    logger.info("Fetching GPU index: %s", args.index_url)
    index_html = fetch_html(
        session,
        args.index_url,
        timeout=args.timeout,
        rate_limiter=rate_limiter,
        logger=logger,
    )
    entries = parse_index_entries(index_html)

    if not entries:
        raise RuntimeError(
            "No GPU detail links were found on the index page. "
            "The page layout may have changed, or the session is not authorized."
        )

    logger.info("Discovered %d GPU entries on the index page", len(entries))

    saved_count = len(records)
    for index, entry in enumerate(entries, start=1):
        if args.limit is not None and saved_count >= args.limit:
            break

        if entry.url in processed_urls:
            logger.info("[%d/%d] Skipping already saved %s", index, len(entries), entry.gpu_name)
            continue

        if should_exclude_by_name(entry.gpu_name):
            logger.info("[%d/%d] Skipping excluded GPU %s", index, len(entries), entry.gpu_name)
            continue

        logger.info("[%d/%d] Fetching %s", index, len(entries), entry.gpu_name)
        try:
            detail_html = fetch_html(
                session,
                entry.url,
                timeout=args.timeout,
                rate_limiter=rate_limiter,
                logger=logger,
            )
        except BotProtectionError:
            raise
        except requests.RequestException as exc:
            logger.warning("Failed to fetch %s: %s", entry.url, exc)
            continue

        soup = BeautifulSoup(detail_html, "html.parser")
        record = build_record(
            soup,
            entry.url,
            entry.gpu_name,
            include_raw_specs=args.include_raw_specs,
        )
        include_record, reason = should_include_record(record)
        if not include_record:
            logger.info(
                "[%d/%d] Excluding %s (%s)",
                index,
                len(entries),
                record.get("gpu_name"),
                reason,
            )
            continue

        records.append(record)
        processed_urls.add(entry.url)
        saved_count += 1
        save_json(records, args.output)
        if args.csv_output:
            save_csv(records, args.csv_output)
        logger.info(
            "[%d/%d] Saved %s (%d total)",
            index,
            len(entries),
            record.get("gpu_name"),
            saved_count,
        )

    save_json(records, args.output)
    if args.csv_output:
        save_csv(records, args.csv_output)

    logger.info("Finished with %d saved GPUs", len(records))
    return 0


def main() -> int:
    args = parse_args()
    logger = configure_logging(args.verbose)

    try:
        return scrape_gpus(args, logger)
    except BotProtectionError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:  # pragma: no cover - top-level failure path
        logger.exception("Scrape failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
