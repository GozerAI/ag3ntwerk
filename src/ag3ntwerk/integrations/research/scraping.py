"""
Web Scraping Integration for ag3ntwerk.

Provides browser automation using Playwright.

Requirements:
    - pip install playwright
    - playwright install

Scraping is ideal for:
    - Competitor analysis
    - Market research
    - Price monitoring
    - Content aggregation
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ScrapingConfig:
    """Configuration for web scraping."""

    headless: bool = True
    browser: str = "chromium"  # chromium, firefox, webkit
    timeout: int = 30000  # milliseconds
    user_agent: str = ""
    viewport_width: int = 1920
    viewport_height: int = 1080
    proxy: Optional[Dict[str, str]] = None


@dataclass
class PageContent:
    """Represents scraped page content."""

    url: str
    title: str = ""
    text: str = ""
    html: str = ""
    links: List[Dict[str, str]] = field(default_factory=list)
    images: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    screenshot: Optional[bytes] = None
    scraped_at: datetime = field(default_factory=datetime.now)


class ScrapingIntegration:
    """
    Integration for web scraping using Playwright.

    Example:
        scraper = ScrapingIntegration()

        # Simple scrape
        content = await scraper.scrape("https://example.com")

        # Extract specific elements
        prices = await scraper.extract_elements(
            "https://shop.com",
            selector=".product-price",
        )

        # Take screenshot
        screenshot = await scraper.screenshot("https://example.com")
    """

    def __init__(self, config: Optional[ScrapingConfig] = None):
        """Initialize scraping integration."""
        self.config = config or ScrapingConfig()
        self._browser = None
        self._playwright = None

    async def _get_browser(self):
        """Get or create browser instance."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()

                browser_type = getattr(self._playwright, self.config.browser)
                self._browser = await browser_type.launch(
                    headless=self.config.headless,
                )
            except ImportError:
                raise ImportError(
                    "playwright not installed. Install with: pip install playwright && playwright install"
                )
        return self._browser

    async def _new_page(self):
        """Create a new page with configured settings."""
        browser = await self._get_browser()
        context = await browser.new_context(
            viewport={
                "width": self.config.viewport_width,
                "height": self.config.viewport_height,
            },
            user_agent=self.config.user_agent or None,
            proxy=self.config.proxy,
        )
        return await context.new_page()

    async def scrape(
        self,
        url: str,
        wait_for: Optional[str] = None,
        extract_links: bool = True,
        extract_images: bool = False,
    ) -> PageContent:
        """
        Scrape a web page.

        Args:
            url: URL to scrape
            wait_for: Selector to wait for
            extract_links: Extract all links
            extract_images: Extract all images

        Returns:
            PageContent with scraped data
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.config.timeout)

            title = await page.title()
            text = await page.inner_text("body")
            html = await page.content()

            # Extract metadata
            metadata = {}
            meta_tags = await page.query_selector_all("meta")
            for tag in meta_tags:
                name = await tag.get_attribute("name") or await tag.get_attribute("property")
                content = await tag.get_attribute("content")
                if name and content:
                    metadata[name] = content

            # Extract links
            links = []
            if extract_links:
                link_elements = await page.query_selector_all("a[href]")
                for link in link_elements:
                    href = await link.get_attribute("href")
                    link_text = await link.inner_text()
                    if href:
                        links.append({"href": href, "text": link_text.strip()})

            # Extract images
            images = []
            if extract_images:
                img_elements = await page.query_selector_all("img[src]")
                for img in img_elements:
                    src = await img.get_attribute("src")
                    alt = await img.get_attribute("alt") or ""
                    if src:
                        images.append({"src": src, "alt": alt})

            return PageContent(
                url=url,
                title=title,
                text=text,
                html=html,
                links=links,
                images=images,
                metadata=metadata,
            )

        finally:
            await page.close()

    async def extract_elements(
        self,
        url: str,
        selector: str,
        attribute: Optional[str] = None,
        wait_for: Optional[str] = None,
    ) -> List[str]:
        """
        Extract elements matching a selector.

        Args:
            url: URL to scrape
            selector: CSS selector
            attribute: Attribute to extract (text content if None)
            wait_for: Selector to wait for

        Returns:
            List of extracted values
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.config.timeout)

            elements = await page.query_selector_all(selector)
            values = []

            for element in elements:
                if attribute:
                    value = await element.get_attribute(attribute)
                else:
                    value = await element.inner_text()

                if value:
                    values.append(value.strip())

            return values

        finally:
            await page.close()

    async def extract_table(
        self,
        url: str,
        selector: str,
        wait_for: Optional[str] = None,
    ) -> List[List[str]]:
        """
        Extract table data.

        Args:
            url: URL to scrape
            selector: Table selector
            wait_for: Selector to wait for

        Returns:
            2D list of table data
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.config.timeout)

            table = await page.query_selector(selector)
            if not table:
                return []

            rows = await table.query_selector_all("tr")
            data = []

            for row in rows:
                cells = await row.query_selector_all("td, th")
                row_data = []
                for cell in cells:
                    text = await cell.inner_text()
                    row_data.append(text.strip())
                if row_data:
                    data.append(row_data)

            return data

        finally:
            await page.close()

    async def screenshot(
        self,
        url: str,
        full_page: bool = False,
        selector: Optional[str] = None,
    ) -> bytes:
        """
        Take a screenshot.

        Args:
            url: URL to screenshot
            full_page: Capture full page
            selector: Specific element to capture

        Returns:
            Screenshot as bytes
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)
            await page.wait_for_load_state("networkidle")

            if selector:
                element = await page.query_selector(selector)
                if element:
                    return await element.screenshot()
                return b""
            else:
                return await page.screenshot(full_page=full_page)

        finally:
            await page.close()

    async def pdf(
        self,
        url: str,
        path: str,
    ) -> str:
        """
        Save page as PDF.

        Args:
            url: URL to convert
            path: Output file path

        Returns:
            Saved file path
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)
            await page.wait_for_load_state("networkidle")
            await page.pdf(path=path)
            return path

        finally:
            await page.close()

    async def fill_form(
        self,
        url: str,
        form_data: Dict[str, str],
        submit_selector: Optional[str] = None,
    ) -> PageContent:
        """
        Fill and optionally submit a form.

        Args:
            url: URL with form
            form_data: Dict mapping selector to value
            submit_selector: Submit button selector

        Returns:
            PageContent after form submission
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)

            for selector, value in form_data.items():
                await page.fill(selector, value)

            if submit_selector:
                await page.click(submit_selector)
                await page.wait_for_load_state("networkidle")

            title = await page.title()
            text = await page.inner_text("body")

            return PageContent(
                url=page.url,
                title=title,
                text=text,
            )

        finally:
            await page.close()

    async def execute_script(
        self,
        url: str,
        script: str,
    ) -> Any:
        """
        Execute JavaScript on a page.

        Args:
            url: URL to load
            script: JavaScript to execute

        Returns:
            Script result
        """
        page = await self._new_page()

        try:
            await page.goto(url, timeout=self.config.timeout)
            return await page.evaluate(script)

        finally:
            await page.close()

    async def close(self):
        """Close browser and cleanup."""
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
