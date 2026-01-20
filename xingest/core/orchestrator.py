"""Pipeline orchestrator - coordinates fetching, parsing, caching."""

import asyncio
from datetime import datetime

from xingest.config import ScraperConfig, CacheBackend
from xingest.cache.sqlite_cache import SQLiteCache
from xingest.cache.base import CacheProvider
from xingest.proxy.rotating import ProxyProvider
from xingest.logging import get_logger, configure_logging
from xingest.core.fetcher import fetch_profile_page
from xingest.core.parser import parse_page
from xingest.core.transformer import transform_result
from xingest.models.result import ScrapeResult
from xingest.exceptions import XingestError


class Scraper:
    """
    High-level scraper interface with caching and proxy support.
    
    Example:
        async with Scraper() as scraper:
            result = await scraper.scrape("elonmusk")
            print(result.profile.followers_count)
    """

    def __init__(self, config: ScraperConfig | None = None):
        """
        Initialize scraper with optional configuration.

        Args:
            config: ScraperConfig instance, uses defaults if None
        """
        self.config = config or ScraperConfig()
        self._cache: CacheProvider | None = None
        self._proxy: ProxyProvider | None = None
        self._log = get_logger("scraper")

    async def __aenter__(self) -> "Scraper":
        """Async context manager entry - initialize resources."""
        configure_logging(self.config)
        
        # Initialize cache
        if self.config.cache_backend == CacheBackend.SQLITE:
            self._cache = SQLiteCache(
                self.config.sqlite_path,
                self.config.cache_ttl_seconds,
            )
        
        # Initialize proxy provider
        if self.config.proxy_urls:
            self._proxy = ProxyProvider(
                self.config.proxy_urls,
                self.config.proxy_mode,
            )
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - cleanup resources."""
        if self._cache:
            await self._cache.close()

    async def scrape(
        self,
        username: str,
        force_refresh: bool = False,
    ) -> ScrapeResult:
        """
        Scrape a single profile with caching.

        Args:
            username: X/Twitter handle (without @)
            force_refresh: Skip cache and fetch fresh data

        Returns:
            ScrapeResult with profile and tweets
        """
        username = username.lstrip("@").lower()
        self._log.info("scrape_start", username=username, force_refresh=force_refresh)

        # Check cache first
        if self._cache and not force_refresh:
            cached = await self._cache.get(username)
            if cached:
                self._log.info("cache_hit", username=username, age_seconds=cached.cache_age_seconds)
                return cached

        # Fetch fresh data
        start = datetime.now()
        proxy = await self._proxy.get_next() if self._proxy else None
        
        fetch_result = await fetch_profile_page(
            username,
            headless=self.config.headless,
            proxy=proxy,
            timeout_ms=self.config.browser_timeout_ms,
        )

        if not fetch_result.success:
            self._log.error("fetch_failed", username=username, error=fetch_result.error)
            return ScrapeResult(
                success=False,
                profile=None,
                tweets=[],
                scraped_at=datetime.now(),
                duration_ms=(datetime.now() - start).total_seconds() * 1000,
            )

        # Parse and transform
        parse_result = parse_page(fetch_result.html, username)
        duration_ms = (datetime.now() - start).total_seconds() * 1000
        
        result = transform_result(parse_result, username, duration_ms)
        
        self._log.info(
            "scrape_complete",
            username=username,
            tweets_count=len(result.tweets),
            duration_ms=duration_ms,
        )

        # Store in cache
        if self._cache and result.success:
            await self._cache.set(username, result)

        return result

    async def scrape_many(
        self,
        usernames: list[str],
        force_refresh: bool = False,
        delay_ms: int | None = None,
    ) -> list[ScrapeResult]:
        """
        Scrape multiple profiles sequentially with delay.

        Args:
            usernames: List of X/Twitter handles
            force_refresh: Skip cache for all
            delay_ms: Delay between requests (uses config default if None)

        Returns:
            List of ScrapeResults in same order as input
        """
        delay = delay_ms if delay_ms is not None else self.config.request_delay_ms
        results = []

        for i, username in enumerate(usernames):
            result = await self.scrape(username, force_refresh)
            results.append(result)

            # Delay between requests (except after last)
            if delay > 0 and i < len(usernames) - 1:
                await asyncio.sleep(delay / 1000)

        return results

    async def invalidate_cache(self, username: str) -> None:
        """Remove a specific username from cache."""
        if self._cache:
            await self._cache.invalidate(username.lstrip("@").lower())

    async def clear_cache(self) -> None:
        """Clear all cached data."""
        if self._cache:
            await self._cache.clear()
