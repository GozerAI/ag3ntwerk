"""
Playwright MCP Integration for ag3ntwerk.

Provides browser automation capabilities using Playwright through MCP protocol.
Allows ag3ntwerk agents to interact with web pages, scrape data, and automate browser tasks.

Requirements:
    - Playwright MCP server running
    - pip install playwright

Setup:
    playwright install chromium
"""

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class BrowserType(str, Enum):
    """Supported browser types."""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"


class WaitState(str, Enum):
    """Page load states for waiting."""

    LOAD = "load"
    DOMCONTENTLOADED = "domcontentloaded"
    NETWORKIDLE = "networkidle"
    COMMIT = "commit"


@dataclass
class Screenshot:
    """Screenshot result."""

    data: bytes
    width: int = 0
    height: int = 0
    path: Optional[str] = None
    format: str = "png"

    def to_base64(self) -> str:
        """Convert screenshot to base64 string."""
        return base64.b64encode(self.data).decode("utf-8")

    def save(self, path: str) -> None:
        """Save screenshot to file."""
        with open(path, "wb") as f:
            f.write(self.data)


@dataclass
class ElementHandle:
    """Represents a DOM element."""

    selector: str
    tag_name: str = ""
    text_content: str = ""
    inner_html: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)
    bounding_box: Optional[Dict[str, float]] = None
    is_visible: bool = True
    is_enabled: bool = True


@dataclass
class Page:
    """Represents a browser page."""

    url: str
    title: str = ""
    content: str = ""
    cookies: List[Dict[str, Any]] = field(default_factory=list)
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})


@dataclass
class BrowserContext:
    """Browser context with isolation."""

    id: str
    browser_type: BrowserType = BrowserType.CHROMIUM
    headless: bool = True
    viewport: Dict[str, int] = field(default_factory=lambda: {"width": 1280, "height": 720})
    user_agent: Optional[str] = None
    locale: str = "en-US"
    timezone: Optional[str] = None
    permissions: List[str] = field(default_factory=list)


class PlaywrightMCP:
    """
    Playwright MCP client for browser automation.

    This client provides browser automation capabilities for ag3ntwerk agents,
    enabling web scraping, form filling, screenshot capture, and more.

    Features:
    - Navigate to URLs
    - Click elements
    - Fill forms
    - Take screenshots
    - Extract page content
    - Execute JavaScript
    - Handle authentication

    Example:
        playwright = PlaywrightMCP()
        await playwright.initialize()

        # Navigate to a page
        await playwright.navigate("https://example.com")

        # Take screenshot
        screenshot = await playwright.screenshot()
        screenshot.save("page.png")

        # Fill a form
        await playwright.fill("input[name='email']", "user@example.com")
        await playwright.click("button[type='submit']")

        # Get page content
        content = await playwright.get_content()
        print(content)

        await playwright.close()
    """

    def __init__(
        self,
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        user_agent: Optional[str] = None,
        timeout: int = 30000,
    ):
        """
        Initialize Playwright MCP client.

        Args:
            browser_type: Browser to use (chromium, firefox, webkit)
            headless: Run browser in headless mode
            viewport: Default viewport size
            user_agent: Custom user agent string
            timeout: Default timeout in milliseconds
        """
        self.browser_type = browser_type
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self.user_agent = user_agent
        self.timeout = timeout

        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    async def initialize(self) -> None:
        """Initialize Playwright and launch browser."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()

        # Launch browser
        browser_launcher = getattr(self._playwright, self.browser_type.value)
        self._browser = await browser_launcher.launch(headless=self.headless)

        # Create context
        context_options = {
            "viewport": self.viewport,
        }
        if self.user_agent:
            context_options["user_agent"] = self.user_agent

        self._context = await self._browser.new_context(**context_options)

        # Create initial page
        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

        logger.info(f"Playwright initialized with {self.browser_type.value}")

    async def close(self) -> None:
        """Close browser and cleanup."""
        if self._page:
            await self._page.close()
            self._page = None

        if self._context:
            await self._context.close()
            self._context = None

        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def navigate(
        self,
        url: str,
        wait_until: WaitState = WaitState.LOAD,
        timeout: Optional[int] = None,
    ) -> Page:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: Wait for this state before returning
            timeout: Navigation timeout in milliseconds

        Returns:
            Page object with URL and title
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.goto(
            url,
            wait_until=wait_until.value,
            timeout=timeout or self.timeout,
        )

        return Page(
            url=self._page.url,
            title=await self._page.title(),
        )

    async def click(
        self,
        selector: str,
        button: str = "left",
        click_count: int = 1,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Click an element.

        Args:
            selector: CSS selector for element
            button: Mouse button (left, right, middle)
            click_count: Number of clicks
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.click(
            selector,
            button=button,
            click_count=click_count,
            timeout=timeout or self.timeout,
        )

    async def fill(
        self,
        selector: str,
        value: str,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Fill an input field.

        Args:
            selector: CSS selector for input
            value: Value to fill
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.fill(
            selector,
            value,
            timeout=timeout or self.timeout,
        )

    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 0,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Type text into an element with optional delay.

        Args:
            selector: CSS selector for element
            text: Text to type
            delay: Delay between keystrokes in milliseconds
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.type(
            selector,
            text,
            delay=delay,
            timeout=timeout or self.timeout,
        )

    async def select_option(
        self,
        selector: str,
        value: Optional[str] = None,
        label: Optional[str] = None,
        index: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> List[str]:
        """
        Select option(s) in a dropdown.

        Args:
            selector: CSS selector for select element
            value: Option value to select
            label: Option label to select
            index: Option index to select
            timeout: Timeout in milliseconds

        Returns:
            List of selected option values
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        options = {}
        if value:
            options["value"] = value
        if label:
            options["label"] = label
        if index is not None:
            options["index"] = index

        return await self._page.select_option(
            selector,
            **options,
            timeout=timeout or self.timeout,
        )

    async def check(
        self,
        selector: str,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Check a checkbox or radio button.

        Args:
            selector: CSS selector for element
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.check(selector, timeout=timeout or self.timeout)

    async def uncheck(
        self,
        selector: str,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Uncheck a checkbox.

        Args:
            selector: CSS selector for element
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.uncheck(selector, timeout=timeout or self.timeout)

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False,
        selector: Optional[str] = None,
        format: str = "png",
        quality: Optional[int] = None,
    ) -> Screenshot:
        """
        Take a screenshot.

        Args:
            path: Optional path to save screenshot
            full_page: Capture full scrollable page
            selector: Capture specific element
            format: Image format (png, jpeg)
            quality: JPEG quality (0-100)

        Returns:
            Screenshot object with image data
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        screenshot_options = {
            "type": format,
            "full_page": full_page,
        }

        if path:
            screenshot_options["path"] = path
        if quality and format == "jpeg":
            screenshot_options["quality"] = quality

        if selector:
            element = await self._page.query_selector(selector)
            if element:
                data = await element.screenshot(**screenshot_options)
            else:
                raise ValueError(f"Element not found: {selector}")
        else:
            data = await self._page.screenshot(**screenshot_options)

        return Screenshot(
            data=data,
            path=path,
            format=format,
        )

    async def get_content(self) -> str:
        """
        Get page HTML content.

        Returns:
            Full HTML content of the page
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        return await self._page.content()

    async def get_text(self, selector: Optional[str] = None) -> str:
        """
        Get text content of page or element.

        Args:
            selector: Optional CSS selector for element

        Returns:
            Text content
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        if selector:
            element = await self._page.query_selector(selector)
            if element:
                return await element.text_content() or ""
            return ""
        else:
            return await self._page.evaluate("document.body.innerText")

    async def get_attribute(
        self,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        """
        Get element attribute value.

        Args:
            selector: CSS selector for element
            attribute: Attribute name

        Returns:
            Attribute value or None
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        return await self._page.get_attribute(selector, attribute)

    async def query_selector(self, selector: str) -> Optional[ElementHandle]:
        """
        Query for a single element.

        Args:
            selector: CSS selector

        Returns:
            ElementHandle or None if not found
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        element = await self._page.query_selector(selector)
        if not element:
            return None

        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        text_content = await element.text_content() or ""
        inner_html = await element.inner_html()
        bounding_box = await element.bounding_box()
        is_visible = await element.is_visible()
        is_enabled = await element.is_enabled()

        return ElementHandle(
            selector=selector,
            tag_name=tag_name,
            text_content=text_content,
            inner_html=inner_html,
            bounding_box=bounding_box,
            is_visible=is_visible,
            is_enabled=is_enabled,
        )

    async def query_selector_all(self, selector: str) -> List[ElementHandle]:
        """
        Query for all matching elements.

        Args:
            selector: CSS selector

        Returns:
            List of ElementHandle objects
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        elements = await self._page.query_selector_all(selector)
        handles = []

        for i, element in enumerate(elements):
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            text_content = await element.text_content() or ""
            is_visible = await element.is_visible()

            handles.append(
                ElementHandle(
                    selector=f"{selector}:nth-child({i+1})",
                    tag_name=tag_name,
                    text_content=text_content,
                    is_visible=is_visible,
                )
            )

        return handles

    async def evaluate(
        self,
        expression: str,
        arg: Optional[Any] = None,
    ) -> Any:
        """
        Execute JavaScript in the page context.

        Args:
            expression: JavaScript expression or function
            arg: Optional argument to pass to function

        Returns:
            Result of JavaScript evaluation
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        if arg:
            return await self._page.evaluate(expression, arg)
        return await self._page.evaluate(expression)

    async def wait_for_selector(
        self,
        selector: str,
        state: str = "visible",
        timeout: Optional[int] = None,
    ) -> Optional[ElementHandle]:
        """
        Wait for element to appear.

        Args:
            selector: CSS selector
            state: State to wait for (attached, detached, visible, hidden)
            timeout: Timeout in milliseconds

        Returns:
            ElementHandle when found
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        element = await self._page.wait_for_selector(
            selector,
            state=state,
            timeout=timeout or self.timeout,
        )

        if not element:
            return None

        tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
        text_content = await element.text_content() or ""

        return ElementHandle(
            selector=selector,
            tag_name=tag_name,
            text_content=text_content,
        )

    async def wait_for_navigation(
        self,
        url: Optional[str] = None,
        wait_until: WaitState = WaitState.LOAD,
        timeout: Optional[int] = None,
    ) -> Page:
        """
        Wait for navigation to complete.

        Args:
            url: Optional URL pattern to wait for
            wait_until: Wait for this state
            timeout: Timeout in milliseconds

        Returns:
            Page object after navigation
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        options = {
            "wait_until": wait_until.value,
            "timeout": timeout or self.timeout,
        }
        if url:
            options["url"] = url

        (
            await self._page.wait_for_url(**options)
            if url
            else await self._page.wait_for_load_state(wait_until.value)
        )

        return Page(
            url=self._page.url,
            title=await self._page.title(),
        )

    async def wait_for_load_state(
        self,
        state: WaitState = WaitState.LOAD,
        timeout: Optional[int] = None,
    ) -> None:
        """
        Wait for page load state.

        Args:
            state: State to wait for
            timeout: Timeout in milliseconds
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.wait_for_load_state(
            state.value,
            timeout=timeout or self.timeout,
        )

    async def scroll_to(
        self,
        x: int = 0,
        y: int = 0,
    ) -> None:
        """
        Scroll to position.

        Args:
            x: Horizontal scroll position
            y: Vertical scroll position
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.evaluate(f"window.scrollTo({x}, {y})")

    async def scroll_into_view(self, selector: str) -> None:
        """
        Scroll element into view.

        Args:
            selector: CSS selector for element
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        element = await self._page.query_selector(selector)
        if element:
            await element.scroll_into_view_if_needed()

    async def set_viewport(
        self,
        width: int,
        height: int,
    ) -> None:
        """
        Set viewport size.

        Args:
            width: Viewport width
            height: Viewport height
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.set_viewport_size({"width": width, "height": height})

    async def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get all cookies.

        Returns:
            List of cookie dictionaries
        """
        if not self._context:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        return await self._context.cookies()

    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Set cookies.

        Args:
            cookies: List of cookie dictionaries
        """
        if not self._context:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._context.add_cookies(cookies)

    async def clear_cookies(self) -> None:
        """Clear all cookies."""
        if not self._context:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._context.clear_cookies()

    async def go_back(self) -> Optional[Page]:
        """
        Navigate back.

        Returns:
            Page after navigation or None if can't go back
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        response = await self._page.go_back()
        if response:
            return Page(
                url=self._page.url,
                title=await self._page.title(),
            )
        return None

    async def go_forward(self) -> Optional[Page]:
        """
        Navigate forward.

        Returns:
            Page after navigation or None if can't go forward
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        response = await self._page.go_forward()
        if response:
            return Page(
                url=self._page.url,
                title=await self._page.title(),
            )
        return None

    async def reload(
        self,
        wait_until: WaitState = WaitState.LOAD,
    ) -> Page:
        """
        Reload the page.

        Args:
            wait_until: Wait for this state

        Returns:
            Page after reload
        """
        if not self._page:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        await self._page.reload(wait_until=wait_until.value)
        return Page(
            url=self._page.url,
            title=await self._page.title(),
        )

    async def new_page(self) -> None:
        """Create a new page and make it active."""
        if not self._context:
            raise RuntimeError("Browser not initialized. Call initialize() first.")

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

    async def close_page(self) -> None:
        """Close current page."""
        if self._page:
            await self._page.close()
            pages = self._context.pages if self._context else []
            self._page = pages[-1] if pages else None

    @property
    def url(self) -> str:
        """Get current page URL."""
        return self._page.url if self._page else ""

    @property
    def title(self) -> str:
        """Get current page title (blocking call)."""
        if not self._page:
            return ""
        # This is a workaround since we can't await in a property
        return ""


class PlaywrightExecutive:
    """
    Wrapper to use Playwright as a ag3ntwerk agent.

    This allows browser automation to be used as an agent
    that can be called by the Nexus orchestrator.

    Example:
        # Create browser agent
        browser_exec = PlaywrightExecutive(
            name="Web Research Assistant",
            domain="research",
        )

        # Execute web task
        result = await browser_exec.execute(
            "Search for recent AI news on Google and summarize"
        )
    """

    def __init__(
        self,
        name: str = "Browser Agent",
        domain: str = "web",
        codename: str = "Navigator",
        browser_type: BrowserType = BrowserType.CHROMIUM,
        headless: bool = True,
    ):
        """
        Initialize Playwright agent.

        Args:
            name: Display name for the agent
            domain: Domain of expertise
            codename: Codename for the agent
            browser_type: Browser to use
            headless: Run browser in headless mode
        """
        self.name = name
        self.domain = domain
        self.codename = codename
        self.browser_type = browser_type
        self.headless = headless
        self._playwright: Optional[PlaywrightMCP] = None

    async def initialize(self) -> None:
        """Initialize browser."""
        self._playwright = PlaywrightMCP(
            browser_type=self.browser_type,
            headless=self.headless,
        )
        await self._playwright.initialize()

    async def close(self) -> None:
        """Close browser."""
        if self._playwright:
            await self._playwright.close()
            self._playwright = None

    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a browser task.

        Note: This is a simplified execution. In practice, you'd want
        to parse the task and execute appropriate browser commands.

        Args:
            task_description: Description of the task
            context: Optional context with URLs, selectors, etc.

        Returns:
            Result dictionary with output and metadata
        """
        if not self._playwright:
            await self.initialize()

        context = context or {}

        # Extract URL from context if provided
        url = context.get("url")
        if url:
            await self._playwright.navigate(url)

        # Take screenshot
        screenshot = await self._playwright.screenshot()

        # Get page content
        content = await self._playwright.get_text()

        return {
            "success": True,
            "url": self._playwright.url,
            "content": content[:5000],  # Truncate for safety
            "screenshot": screenshot.to_base64(),
            "task": task_description,
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
