"""
Amazon UK scraper.
Sets GBP currency cookie before navigating to avoid HUF pricing.
Uses .a-price .a-offscreen for the full price string (most reliable).
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.amazon.co.uk"

SEARCH_QUERIES = [
    "Apple iPhone 16 Pro Max",
    "Apple iPhone 16 Pro",
    "Apple iPhone 16",
    "Apple iPhone 15 Pro",
    "Apple iPhone 15",
    "Samsung Galaxy S25 Ultra",
    "Samsung Galaxy S25 Plus",
    "Samsung Galaxy S25",
    "Samsung Galaxy S24",
    "Google Pixel 9 Pro",
    "Google Pixel 9",
    "OnePlus 13",
    "Nothing Phone 3a",
    "Sony Xperia 1 VI",
]


class AmazonUKScraper(BaseScraper):
    source_id = "amazon_uk"
    source_label = "Amazon UK"
    country = "uk"
    timeout_ms = 30_000

    async def scrape(self, page: Page) -> list[PriceRecord]:
        # Set GBP cookie before any navigation
        await page.context.add_cookies([
            {"name": "i18n-prefs", "value": "GBP", "domain": ".amazon.co.uk", "path": "/"},
            {"name": "lc-acbuk", "value": "en_GB", "domain": ".amazon.co.uk", "path": "/"},
        ])

        all_records: dict[str, PriceRecord] = {}
        for query in SEARCH_QUERIES:
            try:
                results = await self._search(page, query)
                for r in results:
                    asin_match = re.search(r"/dp/([A-Z0-9]{10})", r.url)
                    key = asin_match.group(1) if asin_match else r.raw_name
                    if key not in all_records:
                        all_records[key] = r
            except Exception as e:
                logger.warning(f"[amazon_uk] '{query}' failed: {e}")

        logger.info(f"[amazon_uk] {len(all_records)} unique products")
        return list(all_records.values())

    async def _search(self, page: Page, query: str) -> list[PriceRecord]:
        url = f"{BASE_URL}/s?k={query.replace(' ', '+')}&rh=n%3A5542457031"
        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        await page.wait_for_timeout(2000)

        if await page.query_selector("[action='/errors/validateCaptcha']"):
            raise RuntimeError("Amazon CAPTCHA triggered")

        records = []
        divs = await page.query_selector_all("div[data-component-type='s-search-result']")
        for div in divs[:8]:
            try:
                asin = await div.get_attribute("data-asin")
                title_el = await div.query_selector("h2 span")
                # Use .a-offscreen which has the full price string "£799.00"
                price_el = await div.query_selector(".a-price .a-offscreen")
                link_el = await div.query_selector("h2 a")

                if not title_el or not price_el:
                    continue

                title = (await title_el.inner_text()).strip()
                price_text = (await price_el.inner_text()).strip()
                price = self.parse_price(price_text)

                href = await link_el.get_attribute("href") if link_el else f"/dp/{asin}"
                full_url = href if href.startswith("http") else BASE_URL + href

                # Skip single-word brand headings (e.g. "Apple", "Samsung") and very short names
                if len(title) < 10:
                    continue

                low = title.lower()
                if any(w in low for w in ["case", "cover", "screen protector", "charger", "cable", "holder", "tempered"]):
                    continue

                if title and price and price < 5000:  # sanity check
                    records.append(PriceRecord(
                        raw_name=title,
                        upfront_price=price,
                        monthly_price=None,
                        contract_months=None,
                        url=full_url,
                        currency="GBP",
                    ))
            except Exception as e:
                logger.debug(f"[amazon_uk] parse error: {e}")
        return records
