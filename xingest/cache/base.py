"""Abstract cache interface."""

from abc import ABC, abstractmethod

from xingest.models.result import ScrapeResult


class CacheProvider(ABC):
    """Abstract base class for cache implementations."""

    @abstractmethod
    async def get(self, username: str) -> ScrapeResult | None:
        """
        Retrieve cached result for a username.

        Args:
            username: X/Twitter handle

        Returns:
            Cached ScrapeResult or None if miss/expired
        """
        ...

    @abstractmethod
    async def set(self, username: str, result: ScrapeResult, ttl_seconds: int | None = None) -> None:
        """
        Store result in cache.

        Args:
            username: X/Twitter handle
            result: ScrapeResult to cache
            ttl_seconds: Optional TTL override
        """
        ...

    @abstractmethod
    async def invalidate(self, username: str) -> None:
        """
        Remove specific entry from cache.

        Args:
            username: X/Twitter handle to invalidate
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached entries."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Cleanup connections and resources."""
        ...

    async def __aenter__(self) -> "CacheProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - cleanup."""
        await self.close()
