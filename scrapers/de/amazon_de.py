"""
Amazon Germany scraper.
Sets EUR currency cookie to avoid HUF/wrong-currency pricing.
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.amazon.de"

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
    "OnePlus 15 512GB",
    "OnePlus 15R 256GB",
    "OnePlus 13",
    "Nothing Phone 4a",
    "Nothing Phone 3a",
    "Sony Xperia 1 VII",
    "Sony Xperia 1 VI",
    "Sony Xperia 10 VII",
    "vivo V50",
]


class AmazonDEScraper(BaseScraper):
    source_id = "amazon_de"
    source_label = "Amazon DE"
    country = "de"
    timeout_ms = 30_000

    async def scrape(self, page: Page) -> list[PriceRecord]:
        # Set EUR cookie before any navigation
        await page.context.add_cookies([
            {"name": "i18n-prefs", "value": "EUR", "domain": ".amazon.de", "path": "/"},
            {"name": "lc-acbde", "value": "de_DE", "domain": ".amazon.de", "path": "/"},
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
                logger.warning(f"[amazon_de] '{query}' failed: {e}")

        logger.info(f"[amazon_de] {len(all_records)} unique products")
        return list(all_records.values())

    async def _search(self, page: Page, query: str) -> list[PriceRecord]:
        url = f"{BASE_URL}/s?k={query.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)
        await page.wait_for_timeout(2000)

        if await page.query_selector("[action='/errors/validateCaptcha']"):
            raise RuntimeError("Amazon DE CAPTCHA triggered")

        records = []
        divs = await page.query_selector_all("div[data-component-type='s-search-result']")
        for div in divs[:8]:
            try:
                asin = await div.get_attribute("data-asin")
                title_el = await div.query_selector("h2 span")
                price_el = await div.query_selector(".a-price .a-offscreen")
                link_el = await div.query_selector("h2 a")

                if not title_el or not price_el:
                    continue

                title = (await title_el.inner_text()).strip()
                price_text = (await price_el.inner_text()).strip()

                # German format: "1.049,00 €" — parse_price handles this
                price = self.parse_price(price_text)

                href = await link_el.get_attribute("href") if link_el else f"/dp/{asin}"
                full_url = href if href.startswith("http") else BASE_URL + href

                low = title.lower()
                if any(w in low for w in ["hülle", "schutzfolie", "ladegerät", "kabel", "case", "cover", "halterung"]):
                    continue

                if title and price and price < 5000:
                    records.append(PriceRecord(
                        raw_name=title,
                        upfront_price=price,
                        monthly_price=None,
                        contract_months=None,
                        url=full_url,
                        currency="EUR",
                    ))
            except Exception as e:
                logger.debug(f"[amazon_de] parse error: {e}")
        return records
