"""Proxy rotation utilities."""

import asyncio
import random

from xingest.config import ProxyMode


class ProxyProvider:
    """Manages proxy rotation with configurable selection strategies."""

    def __init__(self, proxy_urls: list[str], mode: ProxyMode = ProxyMode.RANDOM):
        """
        Initialize proxy provider.

        Args:
            proxy_urls: List of proxy URLs (e.g., "http://proxy:8080")
            mode: Selection strategy (round_robin or random)
        """
        self.proxies = proxy_urls
        self.mode = mode
        self._index = 0
        self._lock = asyncio.Lock()

    @property
    def has_proxies(self) -> bool:
        """Check if any proxies are configured."""
        return len(self.proxies) > 0

    async def get_next(self) -> str | None:
        """
        Get next proxy URL based on configured mode.

        Returns:
            Proxy URL string or None if no proxies configured
        """
        if not self.proxies:
            return None

        if self.mode == ProxyMode.NONE:
            return None

        async with self._lock:
            if self.mode == ProxyMode.ROUND_ROBIN:
                proxy = self.proxies[self._index % len(self.proxies)]
                self._index += 1
            else:  # RANDOM
                proxy = random.choice(self.proxies)

        return proxy

    def get_sync(self) -> str | None:
        """
        Synchronous version of get_next for non-async contexts.

        Returns:
            Proxy URL string or None if no proxies configured
        """
        if not self.proxies or self.mode == ProxyMode.NONE:
            return None

        if self.mode == ProxyMode.ROUND_ROBIN:
            proxy = self.proxies[self._index % len(self.proxies)]
            self._index += 1
        else:  # RANDOM
            proxy = random.choice(self.proxies)

        return proxy

    @classmethod
    def from_file(cls, filepath: str, mode: ProxyMode = ProxyMode.RANDOM) -> "ProxyProvider":
        """
        Create ProxyProvider from a file containing proxy URLs (one per line).

        Args:
            filepath: Path to file with proxy URLs
            mode: Selection strategy

        Returns:
            Configured ProxyProvider
        """
        with open(filepath) as f:
            proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        return cls(proxies, mode)
