"""Unit tests for Scraper orchestrator - mocked fetcher, no internet."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from dataclasses import dataclass

from xingest.core.orchestrator import Scraper
from xingest.config import ScraperConfig, CacheBackend
from xingest.models.result import ScrapeResult


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@dataclass
class MockFetchResult:
    """Mock fetch result."""
    success: bool
    html: str = ""
    error: str | None = None


def load_fixture_html(username: str) -> str:
    """Load HTML fixture."""
    html_path = FIXTURES_DIR / f"{username}.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    pytest.skip(f"Fixture not found: {html_path}")


class TestScraperInit:
    """Test Scraper initialization."""

    def test_default_config(self):
        scraper = Scraper()
        assert scraper.config is not None
        assert scraper.config.headless is True

    def test_custom_config(self):
        config = ScraperConfig(headless=False, cache_backend=CacheBackend.NONE)
        scraper = Scraper(config)
        assert scraper.config.headless is False


class TestScraperContextManager:
    """Test async context manager."""

    @pytest.mark.asyncio
    async def test_context_manager_enters(self):
        async with Scraper() as scraper:
            assert scraper is not None

    @pytest.mark.asyncio
    async def test_context_manager_initializes_cache(self, tmp_path):
        config = ScraperConfig(
            cache_backend=CacheBackend.SQLITE,
            sqlite_path=str(tmp_path / "test.db"),
        )
        async with Scraper(config) as scraper:
            assert scraper._cache is not None

    @pytest.mark.asyncio
    async def test_no_cache_when_disabled(self):
        config = ScraperConfig(cache_backend=CacheBackend.NONE)
        async with Scraper(config) as scraper:
            assert scraper._cache is None


class TestScraperScrape:
    """Test scrape method with mocked fetcher."""

    @pytest.mark.asyncio
    async def test_scrape_success(self, tmp_path):
        """Should return valid result when fetch succeeds."""
        html = load_fixture_html("okx")
        mock_result = MockFetchResult(success=True, html=html)
        
        config = ScraperConfig(
            cache_backend=CacheBackend.NONE,
            headless=True,
        )
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                result = await scraper.scrape("okx")
            
            assert result.success is True
            assert result.profile is not None
            assert result.profile.username == "okx"
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_scrape_strips_at_symbol(self, tmp_path):
        """Should handle @username format."""
        html = load_fixture_html("okx")
        mock_result = MockFetchResult(success=True, html=html)
        
        config = ScraperConfig(cache_backend=CacheBackend.NONE)
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                result = await scraper.scrape("@okx")
            
            # Username should be normalized
            assert result.profile.username == "okx"

    @pytest.mark.asyncio
    async def test_scrape_fetch_failure(self):
        """Should handle fetch errors gracefully."""
        mock_result = MockFetchResult(success=False, error="Network error")
        
        config = ScraperConfig(cache_backend=CacheBackend.NONE)
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                result = await scraper.scrape("nonexistent")
            
            assert result.success is False
            assert result.profile is None


class TestScraperCache:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_fetch(self, tmp_path):
        """Should return cached result without fetching."""
        html = load_fixture_html("okx")
        mock_result = MockFetchResult(success=True, html=html)
        
        config = ScraperConfig(
            cache_backend=CacheBackend.SQLITE,
            sqlite_path=str(tmp_path / "test.db"),
            cache_ttl_seconds=60,
        )
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                # First call - should fetch
                result1 = await scraper.scrape("okx")
                # Second call - should use cache
                result2 = await scraper.scrape("okx")
            
            # Fetch should only be called once
            assert mock_fetch.call_count == 1
            assert result2.cached is True

    @pytest.mark.asyncio
    async def test_force_refresh_skips_cache(self, tmp_path):
        """force_refresh=True should bypass cache."""
        html = load_fixture_html("okx")
        mock_result = MockFetchResult(success=True, html=html)
        
        config = ScraperConfig(
            cache_backend=CacheBackend.SQLITE,
            sqlite_path=str(tmp_path / "test.db"),
        )
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                await scraper.scrape("okx")
                await scraper.scrape("okx", force_refresh=True)
            
            # Both calls should fetch
            assert mock_fetch.call_count == 2


class TestScraperMany:
    """Test batch scraping."""

    @pytest.mark.asyncio
    async def test_scrape_many_returns_list(self, tmp_path):
        """Should return results in same order as input."""
        html = load_fixture_html("okx")
        mock_result = MockFetchResult(success=True, html=html)
        
        config = ScraperConfig(
            cache_backend=CacheBackend.NONE,
            request_delay_ms=0,  # No delay for tests
        )
        
        with patch("xingest.core.orchestrator.fetch_profile_page", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_result
            
            async with Scraper(config) as scraper:
                results = await scraper.scrape_many(["okx", "okx"])
            
            assert len(results) == 2
            assert all(r.success for r in results)
