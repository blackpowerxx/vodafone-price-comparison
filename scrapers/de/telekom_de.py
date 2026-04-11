"""
Deutsche Telekom scraper.
Cards use data-qa="LST_ProductCard{n}". Name is on the main anchor's aria-label.
Price is in span.actualText showing "+ X,XX € mtl."
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page, Response
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.telekom.de"
PHONES_URL = f"{BASE_URL}/shop/geraete/smartphones"


class TelekomDEScraper(BaseScraper):
    source_id = "telekom_de"
    source_label = "Telekom DE"
    country = "de"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)
        try:
            await page.wait_for_selector('[data-qa^="LST_ProductCard"]', timeout=15_000)
        except Exception:
            logger.warning("[telekom_de] LST_ProductCard not found, trying scroll")
        await page.wait_for_timeout(2000)

        return await self._scrape_dom(page)

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        cards = await page.query_selector_all('[data-qa^="LST_ProductCard"]')
        logger.info(f"[telekom_de] DOM found {len(cards)} product cards")

        for card in cards:
            try:
                # Name: from the main product anchor's aria-label
                # e.g. "Apple iPhone Air, Verfügbar in 256 GB, 512 GB, 1 TB"
                name_el = await card.query_selector('a[href*="/shop/geraet/"]')
                if not name_el:
                    name_el = await card.query_selector('a[href]')
                if not name_el:
                    continue

                aria = await name_el.get_attribute("aria-label") or ""
                # Take everything before the first comma (strips storage/colour suffix)
                name = aria.split(",")[0].strip()
                if not name or len(name) < 4:
                    # Fallback: use href slug
                    href = await name_el.get_attribute("href") or ""
                    match = re.search(r"/shop/geraet/[^/]+/([^/?]+)", href)
                    name = match.group(1).replace("-", " ").title() if match else ""
                if not name:
                    continue

                # Get storage from aria-label (e.g. "256 GB" after "Verfügbar in")
                storage_match = re.search(r"(\d+)\s*GB", aria, re.I)
                if storage_match:
                    name = f"{name} {storage_match.group(1)}GB"

                # Price: span.actualText contains "+ 21,50 € mtl."
                price_el = await card.query_selector("span.actualText, [class*='actualText'], [class*='price']")
                if not price_el:
                    # Fallback: scan LEAF elements only (no children) that have "€" and "mtl"
                    # Using leaf elements avoids pulling multi-number parent text
                    price_el = await page.evaluate_handle("""(card) => {
                        const els = Array.from(card.querySelectorAll("*"));
                        for (const el of els) {
                            if (el.children.length > 0) continue;  // leaf only
                            const txt = el.textContent.trim();
                            if (txt.includes("€") && (txt.toLowerCase().includes("mtl") || txt.toLowerCase().includes("monat"))) {
                                return el;
                            }
                        }
                        return null;
                    }""", card)
                    if await price_el.evaluate("el => el === null"):
                        price_el = None

                if not price_el:
                    continue

                price_text = (await price_el.inner_text()).strip()
                monthly = self.parse_price(price_text)
                # Sanity check: Telekom monthly prices are between €5 and €200
                if not monthly or monthly > 200 or monthly < 5:
                    continue

                href = await name_el.get_attribute("href") or ""
                url = href if href.startswith("http") else BASE_URL + href

                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=0.0,
                    monthly_price=monthly,
                    contract_months=24,
                    url=url,
                    currency="EUR",
                ))
            except Exception as e:
                logger.debug(f"[telekom_de] card error: {e}")

        return records
