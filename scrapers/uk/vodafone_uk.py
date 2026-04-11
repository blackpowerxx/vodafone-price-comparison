"""
Vodafone UK scraper.
The page fires a HAL session API during load. The second response
contains 'deviceGroups' with all 108 devices and full pricing.
"""
from __future__ import annotations
import logging
from playwright.async_api import Page, Response
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.vodafone.co.uk"
PHONES_URL = f"{BASE_URL}/mobile/pay-monthly-contracts"


class VodafoneUKScraper(BaseScraper):
    source_id = "vodafone_uk"
    source_label = "Vodafone UK"
    country = "uk"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        captured: list[dict] = []

        async def on_response(resp: Response):
            if resp.status == 200 and "json" in resp.headers.get("content-type", ""):
                if "vodafone.co.uk" in resp.url and "api" in resp.url:
                    try:
                        data = await resp.json()
                        if "deviceGroups" in data:
                            captured.append(data)
                    except Exception:
                        pass

        page.on("response", on_response)
        await page.goto(PHONES_URL, wait_until="networkidle", timeout=45_000)
        page.remove_listener("response", on_response)

        if captured:
            records = self._parse_device_groups(captured[0])
            logger.info(f"[vodafone_uk] API yielded {len(records)} devices")
            return records

        # DOM fallback using actual styled-component class pattern
        return await self._scrape_dom(page)

    def _parse_device_groups(self, data: dict) -> list[PriceRecord]:
        records = []
        for group in data.get("deviceGroups", []):
            name = group.get("name")
            if not name:
                continue

            # upfrontPrice and monthlyPrice are nested: {gross: {value: X, uom: "GBP"}}
            def _val(obj):
                if isinstance(obj, dict):
                    gross = obj.get("gross", {})
                    return float(gross.get("value", 0) or 0)
                return 0.0

            upfront = _val(group.get("upfrontPrice", {}))
            monthly = _val(group.get("monthlyPrice", {}))
            tenure = (group.get("planTenure") or {}).get("value") or 24

            # Build URL from make/model
            make = group.get("make", "")
            model = group.get("model", "")
            url = f"{BASE_URL}/mobile/phones/pay-monthly/{make}/{model}" if make and model else PHONES_URL

            # Also try _links
            links = group.get("_links", {})
            for link_key in ("get-handset-pdp", "pdp", "product"):
                if link_key in links:
                    href = links[link_key].get("href", "")
                    if href:
                        url = BASE_URL + href if not href.startswith("http") else href
                        break

            # Skip refurbished items — not comparable to new phone prices
            if "refurbished" in name.lower():
                continue

            if monthly > 0:
                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=upfront,
                    monthly_price=monthly,
                    contract_months=int(tenure),
                    url=url,
                    currency="GBP",
                ))
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        """DOM fallback using Vodafone's styled-component class names."""
        records = []
        # Wait for HandsetCard wrapper to appear
        try:
            await page.wait_for_selector("[class*='HandsetCardstyle__CardWrapper']", timeout=15_000)
        except Exception:
            logger.warning("[vodafone_uk] HandsetCard selector not found")
            return records

        cards = await page.query_selector_all("[class*='HandsetCardstyle__CardWrapper']")
        logger.info(f"[vodafone_uk] DOM found {len(cards)} HandsetCards")

        for card in cards:
            try:
                name_el = await card.query_selector("h3, h2, [class*='Name'], [class*='Title']")
                monthly_el = await card.query_selector("[class*='Monthly'], [class*='monthly'], [class*='Price']")
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
                        currency="GBP",
                    ))
            except Exception as e:
                logger.debug(f"[vodafone_uk] DOM card error: {e}")
        return records
