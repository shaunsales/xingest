"""Playwright-based page fetcher for X/Twitter profiles."""

from dataclasses import dataclass

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

from xingest.exceptions import FetchError, PageBlockedError, ProfileNotFoundError


@dataclass
class FetchResult:
    """Result of a page fetch operation."""

    html: str
    success: bool
    error: str | None = None
    response_status: int | None = None


# Common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


async def fetch_profile_page(
    username: str,
    headless: bool = True,
    timeout_ms: int = 30000,
    user_agent: str | None = None,
    proxy: str | None = None,
) -> FetchResult:
    """
    Fetch the rendered HTML of an X/Twitter profile page.

    Args:
        username: X/Twitter handle (without @)
        headless: Run browser in headless mode
        timeout_ms: Page load timeout in milliseconds
        user_agent: Custom user agent string (uses default rotation if None)
        proxy: Proxy URL (e.g., "http://proxy:8080")

    Returns:
        FetchResult with HTML content or error details
    """
    url = f"https://x.com/{username}"

    async with async_playwright() as p:
        # Browser launch options
        launch_options = {"headless": headless}
        if proxy:
            launch_options["proxy"] = {"server": proxy}

        browser: Browser = await p.chromium.launch(**launch_options)

        try:
            # Create isolated context with fingerprint
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": user_agent or USER_AGENTS[0],
            }
            context: BrowserContext = await browser.new_context(**context_options)
            page: Page = await context.new_page()

            # Navigate to profile
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

            if response is None:
                return FetchResult(
                    html="",
                    success=False,
                    error="No response received",
                )

            status = response.status

            # Check for common error states
            if status == 404:
                raise ProfileNotFoundError(f"Profile @{username} not found")
            if status in (403, 429):
                raise PageBlockedError(f"Blocked or rate limited (HTTP {status})")
            if status >= 400:
                return FetchResult(
                    html="",
                    success=False,
                    error=f"HTTP {status}",
                    response_status=status,
                )

            # Wait for main content to load
            try:
                await page.wait_for_selector(
                    '[data-testid="primaryColumn"]',
                    timeout=timeout_ms,
                )
            except PlaywrightError:
                # Content didn't load, but we may still have usable HTML
                pass

            # Additional wait for tweets to render
            try:
                await page.wait_for_selector(
                    '[data-testid="tweet"]',
                    timeout=5000,
                )
            except PlaywrightError:
                # Tweets may not exist or load slowly
                pass

            # Get rendered HTML
            html = await page.content()

            return FetchResult(
                html=html,
                success=True,
                response_status=status,
            )

        except ProfileNotFoundError:
            raise
        except PageBlockedError:
            raise
        except PlaywrightError as e:
            raise FetchError(f"Browser error: {e}") from e
        except Exception as e:
            raise FetchError(f"Unexpected error: {e}") from e
        finally:
            await browser.close()


async def fetch_profile_page_simple(username: str) -> str:
    """
    Simple wrapper that returns HTML or raises on error.

    Args:
        username: X/Twitter handle (without @)

    Returns:
        Rendered HTML content

    Raises:
        FetchError: If fetch fails
        ProfileNotFoundError: If profile doesn't exist
        PageBlockedError: If blocked/rate limited
    """
    result = await fetch_profile_page(username)
    if not result.success:
        raise FetchError(result.error or "Unknown fetch error")
    return result.html
