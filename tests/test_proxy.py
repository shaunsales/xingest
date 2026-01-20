"""Unit tests for proxy rotation - no internet required."""

import pytest

from xingest.proxy.rotating import ProxyProvider
from xingest.config import ProxyMode


class TestProxyProviderBasics:
    """Test basic proxy provider functionality."""

    def test_empty_proxies(self):
        """Empty proxy list should return None."""
        provider = ProxyProvider([], ProxyMode.RANDOM)
        assert provider.has_proxies is False
        assert provider.get_sync() is None

    def test_has_proxies(self):
        """Should detect when proxies are configured."""
        provider = ProxyProvider(["http://p1:8080"], ProxyMode.RANDOM)
        assert provider.has_proxies is True

    def test_none_mode_returns_none(self):
        """NONE mode should always return None."""
        provider = ProxyProvider(["http://p1:8080"], ProxyMode.NONE)
        assert provider.get_sync() is None


class TestProxyRoundRobin:
    """Test round-robin proxy selection."""

    def test_round_robin_cycles(self):
        """Should cycle through proxies in order."""
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        provider = ProxyProvider(proxies, ProxyMode.ROUND_ROBIN)

        # First cycle
        assert provider.get_sync() == "http://p1:8080"
        assert provider.get_sync() == "http://p2:8080"
        assert provider.get_sync() == "http://p3:8080"
        
        # Second cycle - should wrap around
        assert provider.get_sync() == "http://p1:8080"

    def test_round_robin_single_proxy(self):
        """Single proxy should always return same proxy."""
        provider = ProxyProvider(["http://p1:8080"], ProxyMode.ROUND_ROBIN)
        
        assert provider.get_sync() == "http://p1:8080"
        assert provider.get_sync() == "http://p1:8080"


class TestProxyRandom:
    """Test random proxy selection."""

    def test_random_returns_from_list(self):
        """Random selection should return a proxy from the list."""
        proxies = ["http://p1:8080", "http://p2:8080", "http://p3:8080"]
        provider = ProxyProvider(proxies, ProxyMode.RANDOM)
        
        for _ in range(10):
            proxy = provider.get_sync()
            assert proxy in proxies


class TestProxyAsync:
    """Test async proxy selection."""

    @pytest.mark.asyncio
    async def test_async_round_robin(self):
        """Async round-robin should work correctly."""
        proxies = ["http://p1:8080", "http://p2:8080"]
        provider = ProxyProvider(proxies, ProxyMode.ROUND_ROBIN)
        
        assert await provider.get_next() == "http://p1:8080"
        assert await provider.get_next() == "http://p2:8080"
        assert await provider.get_next() == "http://p1:8080"

    @pytest.mark.asyncio
    async def test_async_empty(self):
        """Async with empty list should return None."""
        provider = ProxyProvider([], ProxyMode.RANDOM)
        assert await provider.get_next() is None

    @pytest.mark.asyncio
    async def test_async_none_mode(self):
        """Async NONE mode should return None."""
        provider = ProxyProvider(["http://p1:8080"], ProxyMode.NONE)
        assert await provider.get_next() is None


class TestProxyFromFile:
    """Test loading proxies from file."""

    def test_load_from_file(self, tmp_path):
        """Should load proxies from file."""
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("http://p1:8080\nhttp://p2:8080\n# comment\n\nhttp://p3:8080")
        
        provider = ProxyProvider.from_file(str(proxy_file), ProxyMode.ROUND_ROBIN)
        
        assert provider.has_proxies
        assert len(provider.proxies) == 3
        assert "http://p1:8080" in provider.proxies
        assert "http://p2:8080" in provider.proxies
        assert "http://p3:8080" in provider.proxies

    def test_load_skips_comments_and_blanks(self, tmp_path):
        """Should skip comments and blank lines."""
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("# Header comment\nhttp://p1:8080\n\n# Another comment\n")
        
        provider = ProxyProvider.from_file(str(proxy_file))
        
        assert len(provider.proxies) == 1
        assert provider.proxies[0] == "http://p1:8080"
