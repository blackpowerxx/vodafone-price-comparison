"""Three UK scraper — similar queue-it pattern to O2 UK."""
from __future__ import annotations

import logging
from playwright.async_api import Page, Response

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)

BASE_URL = "https://www.three.co.uk"
PHONES_URL = f"{BASE_URL}/shop/phones"


class ThreeUKScraper(BaseScraper):
    source_id = "three_uk"
    source_label = "Three UK"
    country = "uk"
    timeout_ms = 60_000

    async def scrape(self, page: Page) -> list[PriceRecord]:
        api_data: list[dict] = []

        async def capture(response: Response):
            url = response.url
            if ("api" in url or "catalog" in url or "product" in url) and response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    try:
                        data = await response.json()
                        api_data.append(data)
                    except Exception:
                        pass

        page.on("response", capture)
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
        try:
            await page.wait_for_selector(
                "[class*='ProductCard'], [class*='product-card'], [class*='device']",
                timeout=15_000,
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)
        page.remove_listener("response", capture)

        # Queue-it check
        if "queue-it.net" in page.url:
            raise RuntimeError("Three UK queue-it active — retry later")

        # Try API responses first
        for data in api_data:
            records = self._parse_api(data)
            if records:
                logger.info(f"[three_uk] API intercepted {len(records)} devices")
                return records

        # JS state
        for expr in ["() => window.__NEXT_DATA__", "() => window.__INITIAL_STATE__"]:
            js_data = await self.get_page_json(page, expr)
            if js_data:
                records = self._walk_for_products(js_data)
                if records:
                    return records

        # DOM fallback
        return await self._scrape_dom(page)

    def _parse_api(self, data) -> list[PriceRecord]:
        records = []
        items = data if isinstance(data, list) else (
            data.get("products") or data.get("results") or data.get("devices") or []
        )
        if not isinstance(items, list):
            return []
        for item in items:
            name = item.get("name") or item.get("displayName")
            monthly = item.get("monthlyPrice") or item.get("payMonthly")
            upfront = item.get("upfrontPrice") or 0
            url = item.get("url") or PHONES_URL
            if name and monthly:
                if isinstance(monthly, str):
                    monthly = self.parse_price(monthly)
                if isinstance(upfront, str):
                    upfront = self.parse_price(upfront) or 0
                if url and not url.startswith("http"):
                    url = BASE_URL + url
                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=float(upfront or 0),
                    monthly_price=float(monthly),
                    contract_months=24,
                    url=url or PHONES_URL,
                ))
        return records

    def _walk_for_products(self, obj, depth=0) -> list[PriceRecord]:
        if depth > 8:
            return []
        records = []
        if isinstance(obj, list) and len(obj) > 2:
            if all(isinstance(i, dict) and ("name" in i or "title" in i or "displayName" in i) for i in obj[:3]):
                return self._parse_api(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                records.extend(self._walk_for_products(v, depth + 1))
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        # Three UK uses MUI + Tailwind; each phone is an <a class='device-card-link-container'>
        cards = await page.query_selector_all("a[class*='device-card-link-container']")
        logger.info(f"[three_uk] DOM found {len(cards)} device-card elements")
        for card in cards:
            try:
                # Name: <p class='... dox-tuk-emphasis-small ...'>Samsung Galaxy S26</p>
                name_el = await card.query_selector("p[class*='dox-tuk-emphasis-small']")
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name or len(name) < 3:
                    continue

                # Monthly price: inside .dox-price-container.price, the .visually-hidden span
                # holds the clean value e.g. "£22.50"
                monthly_container = await card.query_selector(".dox-price-container.price")
                monthly_hidden = await monthly_container.query_selector(".visually-hidden") if monthly_container else None
                monthly = self.parse_price(await monthly_hidden.inner_text()) if monthly_hidden else None

                # Upfront: inside .plus-and-price container
                upfront_container = await card.query_selector(".plus-and-price")
                upfront_hidden = await upfront_container.query_selector(".visually-hidden") if upfront_container else None
                upfront = self.parse_price(await upfront_hidden.inner_text()) if upfront_hidden else 0.0

                href = await card.get_attribute("href") or ""
                url = href if href.startswith("http") else BASE_URL + href

                if name and monthly:
                    records.append(PriceRecord(
                        raw_name=name,
                        upfront_price=float(upfront or 0),
                        monthly_price=monthly,
                        contract_months=36,  # Three UK default is 36 months
                        url=url or PHONES_URL,
                    ))
            except Exception as e:
                logger.debug(f"[three_uk] DOM error: {e}")
        return records
