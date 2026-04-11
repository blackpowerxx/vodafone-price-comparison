"""
O2 Germany (Telefónica) scraper.
The e-shop page fires calls to api-v4.trbo.com which return device+tariff bundles
as structured JSON with name/price fields. We intercept those and return the
cheapest price per device. Falls back to DOM if trbo data insufficient.
"""
from __future__ import annotations
import logging
from playwright.async_api import Page, Response

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.o2online.de"
PHONES_URL = f"{BASE_URL}/e-shop/"


class O2DEScraper(BaseScraper):
    source_id = "o2_de"
    source_label = "O2 DE"
    country = "de"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        trbo_items: list[dict] = []

        async def capture(response: Response):
            if "trbo.com" in response.url and response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        data = await response.json()
                        if isinstance(data, list):
                            trbo_items.extend(data)
                    except Exception:
                        pass

        page.on("response", capture)
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)
        # Dismiss cookie consent (O2 DE uses Usercentrics)
        for sel in [
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Akzeptieren')",
            "[data-testid='uc-accept-all-button']",
            ".uc-btn-accept-all",
        ]:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await page.wait_for_timeout(1500)
                    break
            except Exception:
                pass
        await page.wait_for_timeout(5000)
        page.remove_listener("response", capture)

        logger.info(f"[o2_de] trbo items captured: {len(trbo_items)}")

        if trbo_items:
            return self._parse_trbo(trbo_items)

        # DOM fallback (unlikely to work well without trbo data)
        return await self._scrape_dom(page)

    def _parse_trbo(self, items: list[dict]) -> list[PriceRecord]:
        """
        Parse trbo.com product recommendation API.
        Each item: {name, price (€/month as string e.g. '44.990'), currency, article, ...}
        article contains '__NK__36' or '__NK__24' for contract months.
        Multiple items may appear for the same device at different tariff levels — take min price.
        """
        # Deduplicate: keep minimum price per (name, article_suffix)
        best: dict[str, dict] = {}  # name → best item

        for item in items:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            # Skip non-phone items (earbuds, watches, tablets…)
            if any(kw in name.lower() for kw in ["watch", "buds", "band", "tablet", "pad", "nano sim", "kidswatch"]):
                continue
            price_str = item.get("price") or ""
            try:
                price = float(price_str)
            except (ValueError, TypeError):
                continue
            if price <= 0:
                continue

            # Extract contract months from article field
            article = item.get("article") or ""
            months = 24
            if "NK__36" in article:
                months = 36
            elif "NK__24" in article:
                months = 24

            key = name
            if key not in best or price < best[key]["price"]:
                best[key] = {"item": item, "price": price, "months": months}

        records = []
        for key, entry in best.items():
            item = entry["item"]
            name = item.get("name", "").strip()
            price = entry["price"]
            months = entry["months"]
            records.append(PriceRecord(
                raw_name=name,
                upfront_price=0.0,
                monthly_price=price,
                contract_months=months,
                url=PHONES_URL,
                currency="EUR",
            ))
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        await self.scroll_to_bottom(page)
        # O2 DE uses custom web components (occl-*); most elements have no class
        # Scan for elements with price text near elements with phone names
        cards = await page.query_selector_all(
            "[class*='occl-device'], [class*='product-card'], [class*='ProductCard']"
        )
        logger.info(f"[o2_de] DOM found {len(cards)} cards")
        for card in cards:
            try:
                name_el = await card.query_selector("h3, h2, [class*='name']")
                monthly_el = await card.query_selector("[class*='monthly'], [class*='monat']")
                link_el = await card.query_selector("a[href]")
                if not name_el or not monthly_el:
                    continue
                name = (await name_el.inner_text()).strip()
                monthly = self.parse_price(await monthly_el.inner_text())
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")
                if name and monthly:
                    records.append(PriceRecord(
                        raw_name=name,
                        upfront_price=0.0,
                        monthly_price=monthly,
                        contract_months=24,
                        url=url,
                        currency="EUR",
                    ))
            except Exception as e:
                logger.debug(f"[o2_de] DOM error: {e}")
        return records
