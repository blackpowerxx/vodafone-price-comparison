"""
Vodafone Germany scraper.
Uses the alle-smartphones.html listing page which renders ws10 product cards.
Intercepts the glados API (/glados/v2/hardware/v2) for device list, then falls
back to DOM scraping with ws10-product-card-list classes + ws10-sr-only prices.
"""
from __future__ import annotations
import logging, re
from playwright.async_api import Page, Response
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from base_scraper import BaseScraper, PriceRecord

logger = logging.getLogger(__name__)
BASE_URL = "https://www.vodafone.de"
PHONES_URL = f"{BASE_URL}/privat/handys-tablets-tarife/alle-smartphones.html"


class VodafoneDEScraper(BaseScraper):
    source_id = "vodafone_de"
    source_label = "Vodafone DE"
    country = "de"

    async def scrape(self, page: Page) -> list[PriceRecord]:
        api_data: list[dict] = []

        async def capture(response: Response):
            url = response.url
            if response.status == 200:
                ct = response.headers.get("content-type", "")
                if "json" in ct and "vodafone.de" in url:
                    try:
                        data = await response.json()
                        raw = str(data)
                        if len(raw) > 300 and any(k in raw for k in ["device", "product", "handset", "smartphone", "tariff", "devices"]):
                            api_data.append(data)
                    except Exception:
                        pass

        page.on("response", capture)
        await page.goto(PHONES_URL, wait_until="domcontentloaded", timeout=45_000)

        # Dismiss cookie consent
        await self._dismiss_cookies(page)
        await page.wait_for_timeout(3000)

        # Scroll to load product content
        await self.scroll_to_bottom(page, pause_ms=1200)
        page.remove_listener("response", capture)

        # Try intercepted glados API responses first
        for data in api_data:
            records = self._parse_glados(data)
            if records:
                logger.info(f"[vodafone_de] glados API yielded {len(records)} devices")
                return records

        # DOM fallback with ws10 classes
        return await self._scrape_dom(page)

    async def _dismiss_cookies(self, page: Page):
        """Click Accept/Akzeptieren on cookie popups."""
        selectors = [
            "button:has-text('Alle akzeptieren')",
            "button:has-text('Akzeptieren')",
            "button:has-text('Zustimmen')",
            "button:has-text('Accept all')",
            "button:has-text('Accept')",
            "[id*='cookie'] button",
            "[class*='cookie'] button",
            "[class*='consent'] button",
        ]
        for sel in selectors:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    return
            except Exception:
                pass

    def _parse_glados(self, data) -> list[PriceRecord]:
        """Parse Vodafone DE /glados/v2/hardware/v2 API response."""
        devices = (data.get("data", {}) or {}).get("devices") or []
        if not devices:
            # Also try top-level lists
            devices = data if isinstance(data, list) else (
                data.get("products") or data.get("results") or data.get("devices") or []
            )
        if not isinstance(devices, list) or len(devices) == 0:
            return []

        records = []
        for item in devices:
            name = item.get("modelName") or item.get("name") or item.get("displayName")
            if not name:
                continue

            # Price may be nested in several ways
            monthly = self._extract_price(item, ["monthlyPrice", "monatspreis", "monthlyRate"])
            upfront = self._extract_price(item, ["upfrontPrice", "einmalpreis", "oneTimePrice"]) or 0.0

            hubpage = item.get("hubpage") or {}
            href = hubpage.get("href") if isinstance(hubpage, dict) else None
            url = BASE_URL + href if href else PHONES_URL

            if name and monthly:
                records.append(PriceRecord(
                    raw_name=name,
                    upfront_price=float(upfront),
                    monthly_price=float(monthly),
                    contract_months=24,
                    url=url,
                    currency="EUR",
                ))
        return records

    def _extract_price(self, item, keys):
        for k in keys:
            v = item.get(k)
            if v is None:
                continue
            if isinstance(v, dict):
                v = v.get("gross", {}).get("value") or v.get("value") or v.get("amount")
            if v is not None:
                try:
                    return float(str(v).replace(",", "."))
                except Exception:
                    pass
        return None

    async def _scrape_dom(self, page: Page) -> list[PriceRecord]:
        """DOM scraping using Vodafone ws10 design-system classes."""
        records = []
        cards = await page.query_selector_all(
            "[class*='ws10-product-card-list__item']"
        )
        logger.info(f"[vodafone_de] DOM found {len(cards)} cards")
        for card in cards:
            try:
                # Name: ws10-product-card-list__headline
                name_el = await card.query_selector("[class*='ws10-product-card-list__headline']")
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name or len(name) < 3:
                    continue

                # Monthly price: ws10-sr-only paragraphs contain "ab XX,XX € pro Monat"
                # and "ab X,XX € einmal" (upfront). Find the monthly one.
                monthly = None
                upfront = 0.0
                sr_els = await card.query_selector_all("p.ws10-sr-only, [class*='ws10-sr-only']")
                for sr_el in sr_els:
                    text = (await sr_el.inner_text()).strip()
                    if "pro monat" in text.lower() or "monat" in text.lower():
                        monthly = self.parse_price(text)
                    elif "einmal" in text.lower() and monthly is None:
                        # upfront found before monthly; store it
                        upfront = self.parse_price(text) or 0.0

                if not monthly:
                    # Fallback: find any price-like element in card
                    price_els = await card.query_selector_all("[class*='price'], [class*='Price']")
                    for pe in price_els:
                        txt = (await pe.inner_text()).strip()
                        if "€" in txt:
                            monthly = self.parse_price(txt)
                            if monthly:
                                break

                # Link
                link_el = await card.query_selector("a[href]")
                href = await link_el.get_attribute("href") if link_el else None
                url = href if href and href.startswith("http") else BASE_URL + (href or "")

                if name and monthly:
                    records.append(PriceRecord(
                        raw_name=name,
                        upfront_price=float(upfront or 0),
                        monthly_price=float(monthly),
                        contract_months=24,
                        url=url or PHONES_URL,
                        currency="EUR",
                    ))
            except Exception as e:
                logger.debug(f"[vodafone_de] DOM error: {e}")
        return records
