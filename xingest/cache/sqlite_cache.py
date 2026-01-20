"""SQLite-based cache implementation."""

import json
import time
from pathlib import Path

import aiosqlite

from xingest.cache.base import CacheProvider
from xingest.models.result import ScrapeResult


class SQLiteCache(CacheProvider):
    """SQLite-based local cache using aiosqlite."""

    def __init__(self, db_path: str = ".xingest_cache.db", default_ttl: int = 300):
        """
        Initialize SQLite cache.

        Args:
            db_path: Path to SQLite database file
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self.db_path = Path(db_path)
        self.default_ttl = default_ttl
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        """Ensure database connection and schema exist."""
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    username TEXT PRIMARY KEY,
                    result_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at)"
            )
            await self._db.commit()
        return self._db

    async def get(self, username: str) -> ScrapeResult | None:
        """Retrieve cached result, None if miss or expired."""
        db = await self._ensure_db()
        now = time.time()

        async with db.execute(
            "SELECT result_json, created_at FROM cache WHERE username = ? AND expires_at > ?",
            (username.lower(), now),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        result_json, created_at = row
        result = ScrapeResult.model_validate_json(result_json)

        # Update cache metadata
        result.cached = True
        result.cache_age_seconds = now - created_at

        return result

    async def set(
        self, username: str, result: ScrapeResult, ttl_seconds: int | None = None
    ) -> None:
        """Store result in cache."""
        db = await self._ensure_db()
        now = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expires_at = now + ttl

        # Serialize result to JSON
        result_json = result.model_dump_json()

        await db.execute(
            """
            INSERT OR REPLACE INTO cache (username, result_json, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (username.lower(), result_json, now, expires_at),
        )
        await db.commit()

    async def invalidate(self, username: str) -> None:
        """Remove specific entry."""
        db = await self._ensure_db()
        await db.execute("DELETE FROM cache WHERE username = ?", (username.lower(),))
        await db.commit()

    async def clear(self) -> None:
        """Clear all cached entries."""
        db = await self._ensure_db()
        await db.execute("DELETE FROM cache")
        await db.commit()

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries from cache.

        Returns:
            Number of entries removed
        """
        db = await self._ensure_db()
        now = time.time()
        cursor = await db.execute(
            "DELETE FROM cache WHERE expires_at <= ?", (now,)
        )
        await db.commit()
        return cursor.rowcount

    async def close(self) -> None:
        """Close database connection."""
        if self._db is not None:
            await self._db.close()
            self._db = None
