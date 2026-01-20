"""Unit tests for cache implementations - uses JSON fixtures, no internet."""

import asyncio
import pytest
from pathlib import Path

from xingest.cache.sqlite_cache import SQLiteCache
from xingest.models.result import ScrapeResult


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture_result(username: str) -> ScrapeResult:
    """Load ScrapeResult from JSON fixture."""
    json_path = FIXTURES_DIR / f"{username}.json"
    if not json_path.exists():
        pytest.skip(f"Fixture not found: {json_path}")
    return ScrapeResult.model_validate_json(json_path.read_text())


@pytest.fixture
def cache(tmp_path):
    """Create a temporary SQLite cache for testing."""
    db_path = tmp_path / "test_cache.db"
    return SQLiteCache(str(db_path), default_ttl=60)


@pytest.fixture
def sample_result() -> ScrapeResult:
    """Load a sample ScrapeResult from fixtures."""
    return load_fixture_result("okx")


class TestSQLiteCacheBasics:
    """Test basic cache operations."""

    @pytest.mark.asyncio
    async def test_cache_miss_returns_none(self, cache):
        """Cache miss should return None."""
        async with cache:
            result = await cache.get("nonexistent_user")
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self, cache, sample_result):
        """Should store and retrieve result."""
        async with cache:
            await cache.set("testuser", sample_result)
            retrieved = await cache.get("testuser")
            
            assert retrieved is not None
            assert retrieved.profile.username == sample_result.profile.username
            assert len(retrieved.tweets) == len(sample_result.tweets)

    @pytest.mark.asyncio
    async def test_cache_stores_tweets(self, cache, sample_result):
        """Should preserve tweet data through cache."""
        async with cache:
            await cache.set("testuser", sample_result)
            retrieved = await cache.get("testuser")
            
            assert len(retrieved.tweets) > 0
            original_ids = {t.tweet_id for t in sample_result.tweets}
            cached_ids = {t.tweet_id for t in retrieved.tweets}
            assert original_ids == cached_ids

    @pytest.mark.asyncio
    async def test_cache_invalidate(self, cache, sample_result):
        """Should remove entry on invalidate."""
        async with cache:
            await cache.set("testuser", sample_result)
            await cache.invalidate("testuser")
            
            result = await cache.get("testuser")
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_clear(self, cache, sample_result):
        """Should remove all entries on clear."""
        async with cache:
            await cache.set("user1", sample_result)
            await cache.set("user2", sample_result)
            await cache.clear()
            
            assert await cache.get("user1") is None
            assert await cache.get("user2") is None


class TestSQLiteCacheTTL:
    """Test cache TTL behavior."""

    @pytest.mark.asyncio
    async def test_expired_entry_returns_none(self, tmp_path, sample_result):
        """Expired entries should return None."""
        db_path = tmp_path / "test_cache.db"
        cache = SQLiteCache(str(db_path), default_ttl=0)  # 0 second TTL
        
        async with cache:
            await cache.set("testuser", sample_result)
            # Entry should be expired immediately
            await asyncio.sleep(0.1)
            result = await cache.get("testuser")
            assert result is None

    @pytest.mark.asyncio
    async def test_custom_ttl_per_entry(self, cache, sample_result):
        """Should respect custom TTL per entry."""
        async with cache:
            await cache.set("testuser", sample_result, ttl_seconds=0)
            await asyncio.sleep(0.1)
            
            result = await cache.get("testuser")
            assert result is None


class TestSQLiteCacheMetadata:
    """Test cache metadata handling."""

    @pytest.mark.asyncio
    async def test_cached_flag_set(self, cache, sample_result):
        """Retrieved results should have cached=True."""
        async with cache:
            await cache.set("testuser", sample_result)
            retrieved = await cache.get("testuser")
            
            assert retrieved.cached is True

    @pytest.mark.asyncio
    async def test_cache_age_populated(self, cache, sample_result):
        """Retrieved results should have cache_age_seconds set."""
        async with cache:
            await cache.set("testuser", sample_result)
            await asyncio.sleep(0.1)  # Small delay
            retrieved = await cache.get("testuser")
            
            assert retrieved.cache_age_seconds is not None
            assert retrieved.cache_age_seconds >= 0


class TestSQLiteCacheUsernames:
    """Test username handling."""

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self, cache, sample_result):
        """Username lookups should be case-insensitive."""
        async with cache:
            await cache.set("TestUser", sample_result)
            
            result = await cache.get("testuser")
            assert result is not None
            
            result = await cache.get("TESTUSER")
            assert result is not None
