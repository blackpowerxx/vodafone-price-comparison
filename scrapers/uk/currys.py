"""Currys UK scraper — uses JSON-LD schema first, falls back to DOM."""
from __future__ import annotations

import json
import logging
from playwright.async_api import Page

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.currys.co.uk"
PHONES_URL = f"{BASE_URL}/mobile-phones/smartphones"


class CurrysUKScraper(BaseScraper):
    source_id = "currys"
    source_label = "Currys"
    country = "uk"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)
        # Wait for product content rather than networkidle (never fires on Currys)
        try:
            await page.wait_for_selector(
                "[class*='product'], [class*='Product'], li[data-product-id]",
                timeout=15_000,
            )
        except Exception:
            pass
        await self.scroll_to_bottom(page)

        # Try JSON-LD structured data (most reliable)
        records = await self._parse_json_ld(page)
        if records:
            logger.info(f"[currys] JSON-LD yielded {len(records)} devices")
            return records

        # DOM fallback
        records = await self._scrape_dom(page)
        logger.info(f"[currys] DOM yielded {len(records)} devices")
        return records

    async def _parse_json_ld(self, page: Page) -> list[PriceRecord]:
        records = []
        scripts = await page.query_selector_all("script[type='application/ld+json']")
        for script in scripts:
            try:
                content = await script.inner_text()
                data = json.loads(content)
                # Could be an ItemList or a single Product
                if isinstance(data, dict):
                    items = []
                    if data.get("@type") == "ItemList":
                        items = data.get("itemListElement", [])
                    elif data.get("@type") == "Product":
                        items = [data]
                    for item in items:
                        product = item.get("item", item)
                        name = product.get("name")
                        offers = product.get("offers", {})
                        if isinstance(offers, list):
                            offers = offers[0] if offers else {}
                        price = offers.get("price") or offers.get("lowPrice")
                        url = product.get("url") or offers.get("url") or PHONES_URL
                        if name and price:
                            records.append(PriceRecord(
                                raw_name=name,
                                upfront_price=float(price),
                                monthly_price=None,
                                contract_months=None,
                                url=url if url.startswith("http") else BASE_URL + url,
                                currency="GBP",
                            ))
            except Exception as e:
                logger.debug(f"[currys] JSON-LD parse error: {e}")
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        # Currys product cards
        cards = await page.query_selector_all(
            "[class*='product-item'], [class*='ProductCard'], [class*='product-card'], "
            "li[data-product-id], [data-component='product-tile']"
        )
        for card in cards:
            try:
                name_el = await card.query_selector("[class*='product-name'], [class*='productTitle'], h3, h2")
                price_el = await card.query_selector("[class*='price-value'], [class*='current-price'], [class*='productPrice']")
                link_el = await card.query_selector("a[href]")
                if not name_el or not price_el:
                    continue
                name = (await name_el.inner_text()).strip()
                price = self.parse_price(await price_el.inner_text())
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")
                if name and price:
                    records.append(PriceRecord(
                        raw_name=name,
                        upfront_price=price,
                        monthly_price=None,
                        contract_months=None,
                        url=url,
                        currency="GBP",
                    ))
            except Exception as e:
                logger.debug(f"[currys] DOM card error: {e}")
        return records
