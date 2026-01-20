"""Redis cache implementation."""

import json
import time
from typing import Optional

from xingest.cache.base import CacheProvider
from xingest.models.result import ScrapeResult

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class RedisCache(CacheProvider):
    """
    Redis-based cache provider.

    Requires redis package: pip install redis

    Example:
        cache = RedisCache("redis://localhost:6379/0")
        async with cache:
            await cache.set("elonmusk", result)
            cached = await cache.get("elonmusk")
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0", default_ttl: int = 300):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
        """
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis package not installed. Install with: pip install redis"
            )

        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._client: Optional[redis.Redis] = None
        self._key_prefix = "xingest:"

    async def _ensure_client(self) -> "redis.Redis":
        """Get or create Redis client."""
        if self._client is None:
            self._client = redis.from_url(self.redis_url)
        return self._client

    def _make_key(self, username: str) -> str:
        """Create Redis key for username."""
        return f"{self._key_prefix}{username.lower()}"

    async def get(self, username: str) -> ScrapeResult | None:
        """Retrieve cached result for username."""
        client = await self._ensure_client()
        key = self._make_key(username)

        # Get data and metadata
        pipe = client.pipeline()
        pipe.get(key)
        pipe.get(f"{key}:ts")
        data, timestamp = await pipe.execute()

        if data is None:
            return None

        try:
            result = ScrapeResult.model_validate_json(data)

            # Calculate cache age
            if timestamp:
                cache_age = time.time() - float(timestamp)
                result = result.model_copy(
                    update={"cached": True, "cache_age_seconds": cache_age}
                )
            else:
                result = result.model_copy(update={"cached": True})

            return result
        except Exception:
            # Invalid cached data, remove it
            await self.invalidate(username)
            return None

    async def set(
        self,
        username: str,
        result: ScrapeResult,
        ttl_seconds: int | None = None,
    ) -> None:
        """Cache result for username."""
        client = await self._ensure_client()
        key = self._make_key(username)
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl

        # Store data and timestamp
        pipe = client.pipeline()
        pipe.setex(key, ttl, result.model_dump_json())
        pipe.setex(f"{key}:ts", ttl, str(time.time()))
        await pipe.execute()

    async def invalidate(self, username: str) -> None:
        """Remove cached result for username."""
        client = await self._ensure_client()
        key = self._make_key(username)

        await client.delete(key, f"{key}:ts")

    async def clear(self) -> None:
        """Clear all cached data."""
        client = await self._ensure_client()

        # Find all xingest keys
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=f"{self._key_prefix}*")
            if keys:
                await client.delete(*keys)
            if cursor == 0:
                break

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None

    async def ping(self) -> bool:
        """Check if Redis is available."""
        try:
            client = await self._ensure_client()
            return await client.ping()
        except Exception:
            return False
