"""
EE scraper.
Products live in NEXT_DATA → props.apolloState → ROOT_QUERY →
deviceBundlesSummaries:{...} → deviceBundlesSummaries list.
Each item is a direct dict (not a __ref) with device/plan sub-objects.
"""
from __future__ import annotations
import logging
from playwright.async_api import Page
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.ee.co.uk"
PHONES_URL = f"{BASE_URL}/mobile/pay-monthly-phones-gallery"


class EEScraper(BaseScraper):
    source_id = "ee"
    source_label = "EE"
    country = "uk"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)
        # Wait for the Apollo state to be populated
        try:
            await page.wait_for_function(
                "() => window.__NEXT_DATA__ && window.__NEXT_DATA__.props && window.__NEXT_DATA__.props.apolloState",
                timeout=15_000,
            )
        except Exception:
            pass
        await page.wait_for_timeout(2000)

        nd = await self.get_page_json(page, "() => window.__NEXT_DATA__")
        records = []
        if nd:
            records = self._parse_next_data(nd)
            logger.info(f"[ee] Apollo/NEXT_DATA yielded {len(records)} devices")

        if not records:
            records = await self._scrape_dom(page)
        return records

    def _parse_next_data(self, nd: dict) -> list[PriceRecord]:
        records = []
        apollo = nd.get("props", {}).get("apolloState", {})
        if not apollo:
            return records

        # Products are in ROOT_QUERY under the deviceBundlesSummaries key
        root_query = apollo.get("ROOT_QUERY", {})
        bundles_key = next((k for k in root_query if "deviceBundlesSummaries" in k), None)
        if not bundles_key:
            return records

        summaries = root_query[bundles_key].get("deviceBundlesSummaries", [])

        for item in summaries:
            if not isinstance(item, dict):
                continue
            # Resolve __ref if needed
            if "__ref" in item:
                item = apollo.get(item["__ref"], item)
            if not isinstance(item, dict):
                continue

            # device sub-object (may be __ref)
            device_obj = item.get("device", {})
            if isinstance(device_obj, dict) and "__ref" in device_obj:
                device_obj = apollo.get(device_obj["__ref"], device_obj)

            name = (device_obj.get("displayName") or device_obj.get("name")
                    or item.get("displayName") or item.get("name"))
            if not name:
                continue

            # Price: try deviceBundleVariants first (has actual prices)
            monthly, upfront, url = None, 0.0, PHONES_URL

            variants = item.get("deviceBundleVariants", [])
            for v in variants:
                if isinstance(v, dict) and "__ref" in v:
                    v = apollo.get(v["__ref"], v)
                monthly = (v.get("payMonthlyPrice") or v.get("monthlyCost")
                           or v.get("monthlyPrice"))
                upfront_raw = v.get("upfrontPrice") or v.get("upfrontCost") or 0
                link = v.get("url") or v.get("pdpUrl") or ""
                if monthly is not None:
                    if isinstance(monthly, str): monthly = self.parse_price(monthly)
                    if isinstance(upfront_raw, str): upfront_raw = self.parse_price(upfront_raw) or 0
                    upfront = float(upfront_raw or 0)
                    if link and not link.startswith("http"): link = BASE_URL + link
                    url = link or PHONES_URL
                    break

            # EE price structure: plan monthly + device monthly, upfront = payTodayPrice
            if monthly is None:
                combos = item.get("devicePlanCombinations", [])
                for c in combos:
                    if isinstance(c, dict) and "__ref" in c:
                        c = apollo.get(c["__ref"], c)
                    plan_monthly = (c.get("plan") or {}).get("price", {}).get("payMonthlyPrice") or 0
                    device_monthly = (c.get("productPrice") or {}).get("payMonthlyPrice") or 0
                    today = (c.get("productPrice") or {}).get("payTodayPrice") or 0
                    if plan_monthly or device_monthly:
                        monthly = float(plan_monthly) + float(device_monthly)
                        upfront = float(today)
                        break
                    # Flat price fields (non-loan plans)
                    flat = (c.get("payMonthlyPrice") or c.get("monthlyCost") or c.get("monthlyPrice"))
                    if flat:
                        monthly = float(flat)
                        break

            if name and monthly:
                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=upfront,
                    monthly_price=float(monthly),
                    contract_months=24,
                    url=url,
                    currency="GBP",
                ))
        return records

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        records = []
        cards = await page.query_selector_all(
            "[class*='handset'], [class*='device-card'], [data-testid*='device'], "
            "[class*='ProductCard'], article[class]"
        )
        logger.info(f"[ee] DOM found {len(cards)} cards")
        for card in cards:
            try:
                name_el = await card.query_selector("h3, h2, [class*='name'], [class*='title']")
                monthly_el = await card.query_selector("[class*='monthly'], [class*='per-month']")
                link_el = await card.query_selector("a[href]")
                if not name_el or not monthly_el:
                    continue
                name = (await name_el.inner_text()).strip()
                monthly = self.parse_price(await monthly_el.inner_text())
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")
                if name and monthly:
                    records.append(PriceRecord(
                        raw_name=name, upfront_price=0.0, monthly_price=monthly,
                        contract_months=24, url=url, currency="GBP",
                    ))
            except Exception as e:
                logger.debug(f"[ee] DOM error: {e}")
        return records
