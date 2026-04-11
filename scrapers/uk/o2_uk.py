"""
O2 UK scraper.
Product cards have class 'product-card_card__*' with data-role='card'.
Name is in the aria-label 'Product card for iPhone 17 Pro'.
Price requires scrolling to load lazy cards.
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page, Response
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.o2.co.uk"
PHONES_URL = f"{BASE_URL}/shop/phones"


class O2UKScraper(BaseScraper):
    source_id = "o2_uk"
    source_label = "O2 UK"
    country = "uk"
    timeout_ms = 45_000

    async def scrape(self, page: Page) -> list[PriceRecord]:
        api_data: list[dict] = []

        async def capture(response: Response):
            url = response.url
            if ("o2.co.uk" in url and response.status == 200 and
                    any(k in url for k in ["catalog","product","device","phone","handset"])):
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        data = await response.json()
                        api_data.append(data)
                    except Exception:
                        pass

        page.on("response", capture)
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        await page.wait_for_timeout(5000)
        # Scroll gradually to trigger lazy-loaded product cards
        for offset in [500, 1000, 2000, 3000]:
            await page.evaluate(f"window.scrollTo(0, {offset})")
            await page.wait_for_timeout(1000)
        page.remove_listener("response", capture)

        # Try API first
        for data in api_data:
            records = self._walk_for_products(data)
            if records:
                logger.info(f"[o2_uk] API yielded {len(records)} devices")
                return records

        # DOM: product cards
        return await self._scrape_dom(page)

    def _walk_for_products(self, obj, depth=0) -> list[PriceRecord]:
        if depth > 8:
            return []
        records = []
        if isinstance(obj, list) and len(obj) > 2:
            if all(isinstance(i, dict) and ("name" in i or "title" in i or "displayName" in i) for i in obj[:3]):
                for item in obj:
                    name = item.get("name") or item.get("title") or item.get("displayName")
                    monthly = item.get("monthlyPrice") or item.get("payMonthly") or item.get("monthlyCost")
                    upfront = item.get("upfrontPrice") or item.get("oneOffCost") or 0
                    url = item.get("url") or item.get("pdpUrl") or PHONES_URL
                    if name and monthly:
                        if isinstance(monthly, str): monthly = self.parse_price(monthly)
                        if isinstance(upfront, str): upfront = self.parse_price(upfront) or 0
                        if url and not url.startswith("http"): url = BASE_URL + url
                        records.append(PriceRecord(
                            raw_name=name,
                            upfront_price=float(upfront or 0),
                            monthly_price=float(monthly),
                            contract_months=24,
                            url=url or PHONES_URL,
                            currency="GBP",
                        ))
        elif isinstance(obj, dict):
            for v in obj.values():
                records.extend(self._walk_for_products(v, depth + 1))
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        # O2 UK product cards: class contains 'product-card_card' and data-role='card'
        # OR fallback to selectable-card class
        cards = await page.query_selector_all(
            "[class*='product-card_card'], [class*='selectable-card'], "
            "[data-role='card'][class*='card']"
        )
        logger.info(f"[o2_uk] DOM found {len(cards)} cards")

        for card in cards:
            try:
                # Name from aria-label like "Product card for iPhone 17 Pro"
                name_el = await card.query_selector("[aria-label*='Product card for'], [aria-label*='card for']")
                if not name_el:
                    name_el = await card.query_selector("a[aria-label], span[id]")

                # Price: look for £ amounts
                price_el = await card.query_selector(
                    "[class*='price'], [class*='Price'], [class*='monthly'], [class*='Monthly']"
                )

                if not name_el:
                    continue

                aria = await name_el.get_attribute("aria-label") or ""
                # "Product card for iPhone 17 Pro" → "iPhone 17 Pro"
                name = re.sub(r"^.*?(?:card\s+for|for\s+the)\s+", "", aria, flags=re.I).strip()
                if not name:
                    name = (await name_el.inner_text()).strip()
                if not name or len(name) < 3:
                    continue

                monthly = None
                if price_el:
                    monthly = self.parse_price(await price_el.inner_text())

                # Fallback: scan all text nodes for price
                if not monthly:
                    all_text = await card.inner_text()
                    for line in all_text.split("\n"):
                        if "£" in line and "/mo" in line.lower():
                            monthly = self.parse_price(line)
                            if monthly:
                                break

                link_el = await card.query_selector("a[href*='/shop/']")
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")

                if name and monthly:
                    records.append(PriceRecord(
                        raw_name=name,
                        upfront_price=0.0,
                        monthly_price=monthly,
                        contract_months=24,
                        url=url,
                        currency="GBP",
                    ))
                elif name:
                    # Card visible but no price yet (lazy loaded) — skip
                    pass

            except Exception as e:
                logger.debug(f"[o2_uk] DOM card error: {e}")
        return records
