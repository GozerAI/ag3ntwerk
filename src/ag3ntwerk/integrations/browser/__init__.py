"""
Browser Automation Integrations for ag3ntwerk.

This package provides browser automation capabilities for agents:
- Playwright MCP: Browser automation for web scraping, testing, and interaction
"""

from ag3ntwerk.integrations.browser.playwright_mcp import (
    PlaywrightMCP,
    BrowserContext,
    Page,
    ElementHandle,
    Screenshot,
)

__all__ = [
    "PlaywrightMCP",
    "BrowserContext",
    "Page",
    "ElementHandle",
    "Screenshot",
]
