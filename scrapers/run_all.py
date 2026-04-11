"""
Orchestrator — runs all scrapers concurrently (max 3 browsers at once),
merges results, writes JSON to data/.
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Add scrapers root to path
sys.path.insert(0, str(Path(__file__).parent))

from uk.vodafone_uk import VodafoneUKScraper
from uk.ee import EEScraper
from uk.o2_uk import O2UKScraper
from uk.three_uk import ThreeUKScraper
from uk.amazon_uk import AmazonUKScraper
from uk.currys import CurrysUKScraper
from de.vodafone_de import VodafoneDEScraper
from de.telekom_de import TelekomDEScraper
from de.o2_de import O2DEScraper
from de.amazon_de import AmazonDEScraper
from de.mediamarkt_de import MediaMarktDEScraper
from normalize import DeviceCatalog, normalize_records

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

UK_SOURCES = ["vodafone_uk", "ee", "o2_uk", "three_uk", "amazon_uk", "currys"]
DE_SOURCES = ["vodafone_de", "telekom_de", "o2_de", "amazon_de", "mediamarkt_de"]

ALL_SCRAPERS = [
    VodafoneUKScraper(),
    EEScraper(),
    O2UKScraper(),
    ThreeUKScraper(),
    AmazonUKScraper(),
    CurrysUKScraper(),
    VodafoneDEScraper(),
    TelekomDEScraper(),
    O2DEScraper(),
    AmazonDEScraper(),
    MediaMarktDEScraper(),
]


async def run_with_semaphore(sem: asyncio.Semaphore, scraper):
    async with sem:
        return await scraper.run()


async def main():
    start = datetime.now(timezone.utc)
    logger.info(f"Starting scrape run at {start.isoformat()}")

    sem = asyncio.Semaphore(3)  # max 3 concurrent browsers
    tasks = [run_with_semaphore(sem, s) for s in ALL_SCRAPERS]
    results = await asyncio.gather(*tasks)

    catalog = DeviceCatalog()
    unmatched: list[dict] = []

    uk_prices: dict[str, dict] = {}
    de_prices: dict[str, dict] = {}
    meta_sources: dict[str, dict] = {}

    for source_id, records, error in results:
        if error:
            meta_sources[source_id] = {
                "status": "error",
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "error": error,
                "device_count": 0,
            }
            logger.warning(f"  {source_id}: FAILED — {error}")
            continue

        normalized = normalize_records(records, catalog, unmatched, source_id)
        count = len(normalized)

        if source_id in UK_SOURCES:
            for nid, price_dict in normalized.items():
                if nid not in uk_prices:
                    uk_prices[nid] = {}
                uk_prices[nid][source_id] = price_dict
        else:
            for nid, price_dict in normalized.items():
                if nid not in de_prices:
                    de_prices[nid] = {}
                de_prices[nid][source_id] = price_dict

        meta_sources[source_id] = {
            "status": "ok",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "device_count": count,
        }
        logger.info(f"  {source_id}: OK — {count} devices")

    # Save catalog (may have new entries)
    catalog.save()

    # Save UK prices
    _write_json(DATA_DIR / "prices_uk.json", {
        "scraped_at": start.isoformat(),
        "prices": uk_prices,
    })

    # Save DE prices
    _write_json(DATA_DIR / "prices_de.json", {
        "scraped_at": start.isoformat(),
        "prices": de_prices,
    })

    # Save meta
    _write_json(DATA_DIR / "meta.json", {
        "last_full_scrape": start.isoformat(),
        "sources": meta_sources,
    })

    # Save unmatched for review
    existing_unmatched = []
    unmatched_path = DATA_DIR / "unmatched.json"
    if unmatched_path.exists():
        with open(unmatched_path) as f:
            existing_unmatched = json.load(f).get("unmatched", [])
    # Dedupe by suggested_id
    seen = {u["suggested_id"] for u in existing_unmatched}
    new_unmatched = [u for u in unmatched if u["suggested_id"] not in seen]
    _write_json(unmatched_path, {"unmatched": existing_unmatched + new_unmatched})

    end = datetime.now(timezone.utc)
    duration = (end - start).seconds
    ok_count = sum(1 for s in meta_sources.values() if s["status"] == "ok")
    logger.info(
        f"Done in {duration}s — {ok_count}/{len(ALL_SCRAPERS)} sources OK, "
        f"{len(uk_prices)} UK devices, {len(de_prices)} DE devices"
    )


def _write_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(f"Wrote {path.name} ({path.stat().st_size // 1024}KB)")


if __name__ == "__main__":
    asyncio.run(main())
