"""
Device name normalization: parse raw strings into structured fields,
then fuzzy-match against the device catalog.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process
from slugify import slugify

DATA_DIR = Path(__file__).parent.parent / "data"

# --- Brand detection ---

BRAND_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bapple\b|\biphone\b", re.I), "Apple"),
    (re.compile(r"\bsamsung\b|\bgalaxy\b", re.I), "Samsung"),
    (re.compile(r"\bgoogle\b|\bpixel\b", re.I), "Google"),
    (re.compile(r"\boneplus\b|\bone\s*plus\b", re.I), "OnePlus"),
    (re.compile(r"\bnothing\b|\bphone\s*\(", re.I), "Nothing"),
    (re.compile(r"\boppo\b", re.I), "OPPO"),
    (re.compile(r"\bxiaomi\b|\bredmi\b|\bpoco\b", re.I), "Xiaomi"),
    (re.compile(r"\bmotorola\b|\bmoto\b", re.I), "Motorola"),
    (re.compile(r"\bhuawei\b", re.I), "Huawei"),
    (re.compile(r"\bvivo\b", re.I), "vivo"),  # before Sony: "50MP Sony IMX..." in vivo titles
    (re.compile(r"\bsony\b|\bxperia\b", re.I), "Sony"),
    (re.compile(r"\bnokia\b", re.I), "Nokia"),
]

STORAGE_PATTERN = re.compile(r"(\d+)\s*GB", re.I)

NOISE_WORDS = re.compile(
    r"\b(with|and|new|the|5g|4g|lte|"
    r"dual[\s\-]*sim|single[\s\-]*sim|e[\s\-]*sim|unlocked|sim[\s\-]*free|"
    r"black|white|silver|gold|titanium|natural|midnight|starlight|sierra|"
    r"blue|green|purple|graphite|space\s*gr[ae]y|pink|yellow|red|coral|"
    r"lavender|sage|charcoal|obsidian|onyx|snow|hazel|bay|lemongrass|"
    r"phantom|prism|cream|mint|sand|lilac|cotton|lime|"
    # German color names
    r"schwarz|weiss|weiß|titangrau|marineblau|silberblau|mintgrün|minzgrün|tiefblau|"
    r"cosmic|orange|"
    r"refurbished|renewed|grade|open\s*box|very\s*good|good|acceptable|"
    r"pristine|great|basic|erneuert|"  # condition grades (Vodafone UK refurbished)
    # German noise words from Amazon DE verbose titles
    r"smartphone|handy|ohne\s*vertrag|mit\s*vertrag|ohne\s*sim\s*lock|"
    r"generaluberholt|generalüberholt|sim\s*lock\s*frei|"
    r"android|display|kamera|dreifach|dreifachkamera|akku|chip|speicher|interner|farbe|zoll|"
    r"ai|ki|tri|ram|intern|extern|wifi|wlan|bluetooth|nfc|"
    r"herstellergarantie|jahre|exklusiv|auf|amazon|entwickelt\s*fur|"
    r"entwickelt\s*für|fur|für|mit|von|und|oder|der|die|das|"
    r"ohne|eu|branding|simlock|weitere|angebote|ois|storage|camera|"
    # Spec noise: display tech, resolution, camera partnerships, chip brands
    r"oled|amoled|lcd|tft|ips|fhd|qhd|uhd|hdr|"
    r"snapdragon|dimensity|exynos|tensor|helio|mediatek|qualcomm|"
    r"zeiss|leica|hasselblad|"
    r"essential)\b",
    # NOTE: 'ultra', 'plus', 'pro', 'max' are kept as model identifiers
    re.I,
)

# Truncate verbose titles at colon, em-dash, " - " separator, or " / " (RAM/storage split in Amazon DE)
TITLE_TRUNCATE = re.compile(r"([:–—]|\s+-\s+|\s+/\s+).+$")


@dataclass
class ParsedDevice:
    raw_name: str
    brand: str | None
    clean_name: str
    storage_gb: int | None

    @property
    def search_query(self) -> str:
        parts = []
        if self.brand:
            parts.append(self.brand)
        parts.append(self.clean_name)
        # Only include storage if it's a plausible storage size (≥32GB); smaller values are likely RAM
        if self.storage_gb and self.storage_gb >= 32:
            parts.append(f"{self.storage_gb}GB")
        return " ".join(parts)

    @property
    def normalized_id(self) -> str:
        return slugify(self.search_query)


def parse_device_name(raw: str) -> ParsedDevice:
    brand = None
    for pattern, brand_name in BRAND_PATTERNS:
        if pattern.search(raw):
            brand = brand_name
            break

    # Use LAST GB match to prefer storage over RAM (e.g. "12GB RAM 256GB" → 256)
    storage_matches = STORAGE_PATTERN.findall(raw)
    if storage_matches:
        # Prefer values >= 32 (storage sizes), otherwise take last match
        large = [int(m) for m in storage_matches if int(m) >= 32]
        storage_gb = large[-1] if large else int(storage_matches[-1])
    else:
        storage_gb = None

    # Truncate at colon/em-dash/" - "/ " / " (removes verbose descriptions and spec lists)
    truncated = TITLE_TRUNCATE.sub("", raw).strip()
    # Strip battery capacity numbers before other processing (e.g. "5.000mAh", "4500mAh")
    truncated = re.sub(r'\d[\d.,]*\s*mah\b', '', truncated, flags=re.I).strip()
    # Strip trailing "(Weitere Angebote, Color, Storage)" style parentheticals (Amazon DE variant selector)
    truncated = re.sub(r'\s*\([^)]*,[^)]*\)\s*$', '', truncated).strip()
    # Normalize "+" suffix to "Plus" (e.g. "Galaxy S25+" → "Galaxy S25 Plus")
    truncated = re.sub(r'(\w)\+(?=\s|$|[,;])', r'\1 Plus', truncated)
    # Also truncate at first comma for long verbose titles (Amazon DE format)
    # Only when the text before the comma is already a meaningful name (>12 chars)
    if len(truncated) > 40:
        comma_pos = truncated.find(',')
        if comma_pos > 12:
            truncated = truncated[:comma_pos].strip()

    cleaned = STORAGE_PATTERN.sub("", truncated)
    # Strip NNmp camera megapixel specs that don't have a word boundary before the number
    cleaned = re.sub(r'\d+\s*mp\b', '', cleaned, flags=re.I)
    # Strip Samsung model numbers (e.g. SM-S931BDBDEUB)
    cleaned = re.sub(r'\bSM-[A-Z]\d{3}[A-Z0-9]*\b', '', cleaned, flags=re.I)
    cleaned = NOISE_WORDS.sub("", cleaned)
    # Also strip German sim-free variants not caught by NOISE_WORDS (e.g. "SIM-freies")
    cleaned = re.sub(r'\bsim[\s\-]*frei[a-z]*\b', '', cleaned, flags=re.I)
    # Remove brand name from clean_name to avoid duplication in slug
    if brand:
        cleaned = re.sub(re.escape(brand), "", cleaned, flags=re.I)
        # Strip ALL-CAPS brand variant "GALAXY" (appears in German Amazon model-number titles)
        if brand == "Samsung":
            cleaned = re.sub(r'\bGALAXY\b', '', cleaned)
    # Remove leftover punctuation / extra whitespace
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip screen size fragments like "6 2" or "6 7" (from "6.2"" after punctuation strip)
    cleaned = re.sub(r'\b6\s+[0-9]\b', '', cleaned).strip()
    # Strip stray size descriptors
    cleaned = re.sub(r'\bone\s+size\b', '', cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return ParsedDevice(
        raw_name=raw,
        brand=brand,
        clean_name=cleaned,
        storage_gb=storage_gb,
    )


class DeviceCatalog:
    """Loads devices.json and provides fuzzy-match lookup."""

    def __init__(self):
        catalog_path = DATA_DIR / "devices.json"
        if catalog_path.exists():
            with open(catalog_path) as f:
                data = json.load(f)
            self._devices: list[dict] = data["devices"]
        else:
            self._devices = []

        # Build corpus: normalized_id -> search string (canonical + aliases)
        self._corpus: dict[str, str] = {}
        for device in self._devices:
            nid = device["normalized_id"]
            self._corpus[nid] = device["canonical_name"]
            for alias in device.get("aliases", []):
                self._corpus[f"{nid}||{alias}"] = alias

    def find(self, parsed: ParsedDevice, cutoff: int = 82) -> str | None:
        """Return normalized_id for best match, or None if below cutoff."""
        if not self._corpus:
            # No catalog yet — auto-generate an ID from the parsed name
            return parsed.normalized_id

        match = process.extractOne(
            parsed.search_query,
            self._corpus,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=cutoff,
        )
        if match is None:
            return None
        key = match[2]
        return key.split("||")[0]  # strip alias suffix

    def add_device(self, parsed: ParsedDevice) -> str:
        """Add a new device to the in-memory catalog and return its normalized_id."""
        nid = parsed.normalized_id
        entry = {
            "normalized_id": nid,
            "canonical_name": parsed.search_query,
            "brand": parsed.brand or "Unknown",
            "model": parsed.clean_name,
            "storage_gb": parsed.storage_gb,
            "aliases": [parsed.raw_name],
        }
        self._devices.append(entry)
        self._corpus[nid] = parsed.search_query
        return nid

    def save(self):
        """Persist updated catalog back to devices.json."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "devices.json", "w") as f:
            json.dump({"devices": self._devices}, f, indent=2)


def normalize_records(
    records: list,  # list of PriceRecord
    catalog: DeviceCatalog,
    unmatched: list[dict],
    source_id: str,
) -> dict[str, dict]:
    """
    Map a list of PriceRecord to { normalized_id: price_dict }.
    Devices that can't be matched are appended to unmatched.
    """
    result: dict[str, dict] = {}
    for record in records:
        parsed = parse_device_name(record.raw_name)
        nid = catalog.find(parsed)

        if nid is None:
            # Log for review but do NOT auto-add to catalog.
            # Catalog is manually curated — run normalize.py --review to inspect unmatched.
            suggested = parsed.normalized_id
            unmatched.append(
                {
                    "source": source_id,
                    "raw_name": record.raw_name,
                    "scraped_at": record.scraped_at,
                    "suggested_id": suggested,
                }
            )
            continue  # skip — don't pollute catalog

        result[nid] = record.to_dict()

    return result
