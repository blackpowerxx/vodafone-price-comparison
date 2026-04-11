"""
Base scraper class with Playwright stealth, retry logic, and network interception.
All site-specific scrapers inherit from this.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Response

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


class PriceRecord:
    def __init__(
        self,
        raw_name: str,
        upfront_price: float | None,
        monthly_price: float | None,
        contract_months: int | None,
        url: str,
        in_stock: bool = True,
        currency: str = "GBP",
    ):
        self.raw_name = raw_name
        self.upfront_price = upfront_price
        self.monthly_price = monthly_price
        self.contract_months = contract_months
        self.url = url
        self.in_stock = in_stock
        self.currency = currency
        self.scraped_at = datetime.now(timezone.utc).isoformat()

        if monthly_price is not None and contract_months is not None:
            self.total_cost = round(
                (upfront_price or 0) + monthly_price * contract_months, 2
            )
        elif upfront_price is not None:
            self.total_cost = upfront_price
        else:
            self.total_cost = None

    def to_dict(self) -> dict:
        return {
            "upfront_price": self.upfront_price,
            "monthly_price": self.monthly_price,
            "contract_months": self.contract_months,
            "total_cost": self.total_cost,
            "url": self.url,
            "in_stock": self.in_stock,
            "currency": self.currency,
            "scraped_at": self.scraped_at,
        }


class BaseScraper(ABC):
    source_id: str = ""       # e.g. "vodafone_uk"
    source_label: str = ""    # e.g. "Vodafone UK"
    country: str = ""         # "uk" or "de"
    max_retries: int = 3
    timeout_ms: int = 30_000

    def __init__(self):
        self._captured_responses: list[dict] = []

    @abstractmethod
    async def scrape(self, page: Page) -> list[PriceRecord]:
        """Implement per-site scraping logic. Returns list of PriceRecord."""
        ...

    async def run(self) -> tuple[str, list[PriceRecord] | None, str | None]:
        """Run scraper with retry logic. Returns (source_id, records, error)."""
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[{self.source_id}] Attempt {attempt}/{self.max_retries}")
                records = await self._run_once()
                logger.info(f"[{self.source_id}] OK — {len(records)} devices")
                return self.source_id, records, None
            except Exception as e:
                last_error = str(e)
                logger.warning(f"[{self.source_id}] Attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)  # backoff: 2s, 4s

        logger.error(f"[{self.source_id}] All attempts failed: {last_error}")
        return self.source_id, None, last_error

    async def _run_once(self) -> list[PriceRecord]:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ],
            )
            ctx = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1440, "height": 900},
                locale="en-GB" if self.country == "uk" else "de-DE",
                timezone_id="Europe/London" if self.country == "uk" else "Europe/Berlin",
                extra_http_headers={
                    "Accept-Language": "en-GB,en;q=0.9" if self.country == "uk" else "de-DE,de;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                },
            )
            # Mask automation indicators
            await ctx.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
            """)
            page = await ctx.new_page()
            page.set_default_timeout(self.timeout_ms)

            try:
                records = await self.scrape(page)
            finally:
                await browser.close()

        return records

    # --- Helpers ---

    async def get_page_json(self, page: Page, js_expr: str) -> Any | None:
        """Evaluate a JS expression and return parsed JSON, or None if absent."""
        try:
            result = await page.evaluate(js_expr)
            return result
        except Exception:
            return None

    async def intercept_json(
        self, page: Page, url_fragment: str, navigate_url: str
    ) -> dict | list | None:
        """
        Navigate to a URL while intercepting any JSON response whose URL contains
        url_fragment. Returns the first matching response body.
        """
        captured: list[dict | list] = []

        async def on_response(response: Response):
            if url_fragment in response.url:
                try:
                    ct = response.headers.get("content-type", "")
                    if "json" in ct:
                        data = await response.json()
                        captured.append(data)
                except Exception:
                    pass

        page.on("response", on_response)
        await page.goto(navigate_url, wait_until="networkidle", timeout=self.timeout_ms)
        page.remove_listener("response", on_response)

        return captured[0] if captured else None

    async def scroll_to_bottom(self, page: Page, pause_ms: int = 1500):
        """Scroll page to bottom to trigger lazy-load."""
        prev_height = 0
        while True:
            height = await page.evaluate("document.body.scrollHeight")
            if height == prev_height:
                break
            prev_height = height
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(pause_ms)

    @staticmethod
    def parse_price(text: str) -> float | None:
        """
        Extract a float price from a string like '£42.99', '42,99 €', or 'ab 21,50 € mtl.'.
        Handles both UK (dot decimal) and German (comma decimal, dot thousands) formats.
        Returns None if no valid price found.
        """
        import re
        if not text:
            return None
        # Find the first price-like pattern: digits with optional thousand-separators
        # Match formats: 1.049,00  /  1,049.00  /  42.99  /  42,99  /  1049  etc.
        # Try German format first (comma as decimal): "1.049,00" or "21,50"
        m_de = re.search(r'\b(\d{1,3}(?:\.\d{3})*),(\d{2})\b', text)
        if m_de:
            return float(m_de.group(1).replace(".", "") + "." + m_de.group(2))
        # Try UK/plain format: "1,049.00" or "42.99" or "42.9"
        m_uk = re.search(r'\b(\d{1,3}(?:,\d{3})*|\d+)\.(\d{1,2})\b', text)
        if m_uk:
            return float(m_uk.group(1).replace(",", "") + "." + m_uk.group(2))
        # Integer-only: "49 €"
        m_int = re.search(r'\b(\d{2,5})\b', text)
        if m_int:
            v = float(m_int.group(1))
            return v if 1 < v < 100_000 else None
        return None
