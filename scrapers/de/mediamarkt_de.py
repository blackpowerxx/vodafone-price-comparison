"""
MediaMarkt Germany scraper.
The category URL returns 0 results (bot-detection). The search URL
?query=smartphone redirects to a real category with products loaded server-side.
Cards use data-test='mms-product-card'; name is data-test='product-title';
price is found via visually-hidden spans (.mms-ui-mBgaT) — we take the minimum
visible price (discounted < UVP).
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page, Response

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.mediamarkt.de"
PHONES_URL = f"{BASE_URL}/de/search.html?query=smartphone"


class MediaMarktDEScraper(BaseScraper):
    source_id = "mediamarkt_de"
    source_label = "MediaMarkt DE"
    country = "de"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)
        try:
            await page.wait_for_selector("[data-test='mms-product-card']", timeout=20_000)
        except Exception:
            pass
        # Scroll to load more products
        await self.scroll_to_bottom(page, pause_ms=1000)
        records = await self._scrape_dom(page)
        logger.info(f"[mediamarkt_de] DOM yielded {len(records)} devices")
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        cards = await page.query_selector_all("[data-test='mms-product-card']")
        logger.info(f"[mediamarkt_de] found {len(cards)} product cards")
        for card in cards:
            try:
                # Name
                name_el = await card.query_selector("[data-test='product-title']")
                if not name_el:
                    name_el = await card.query_selector("p[class], h3, h2")
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name or len(name) < 4:
                    continue

                # Skip accessories / non-phone items
                if any(kw in name.lower() for kw in ["hülle", "case", "folie", "schutz", "ladegerät", "kabel", "kopfhörer"]):
                    continue

                # Price: visually-hidden spans (.mms-ui-mBgaT) contain clean "105,00€"
                # Structure: old-UVP span → current-price span (in that order).
                # Take the LAST such span with a value >= €80 (avoids installment fractions).
                price = None
                # Strategy 1: find hidden price spans — take the last one >= €80
                hidden_spans = await card.query_selector_all("span.mms-ui-mBgaT")
                prices_found = []
                for span in hidden_spans:
                    txt = (await span.inner_text()).strip()
                    p = self.parse_price(txt)
                    if p and 80 < p < 5000:
                        prices_found.append(p)
                if prices_found:
                    # Last qualifying price is the current (possibly discounted) price
                    price = prices_found[-1]

                # Strategy 2: scan the price section inner text
                if not price:
                    price_section = await card.query_selector("[data-test*='product-price'], [data-test='cofr-price']")
                    if price_section:
                        all_text = await price_section.inner_text()
                        found = [self.parse_price(m.group()) for m in re.finditer(r'[\d.]+,\d{2}\s*€', all_text)]
                        found = [p for p in found if p and 80 < p < 5000]
                        if found:
                            price = found[-1]

                if not price:
                    continue

                # URL
                link_el = await card.query_selector("a[href]")
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")

                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=float(price),
                    monthly_price=None,
                    contract_months=None,
                    url=url or PHONES_URL,
                    currency="EUR",
                ))
            except Exception as e:
                logger.debug(f"[mediamarkt_de] DOM error: {e}")
        return records
