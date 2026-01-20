"""Unit tests for configuration management."""

import os
import pytest

from xingest.config import ScraperConfig, ProxyMode, CacheBackend, LogFormat


class TestScraperConfigDefaults:
    """Test default configuration values."""

    def test_default_headless(self):
        config = ScraperConfig()
        assert config.headless is True

    def test_default_timeout(self):
        config = ScraperConfig()
        assert config.browser_timeout_ms == 30000

    def test_default_cache_backend(self):
        config = ScraperConfig()
        assert config.cache_backend == CacheBackend.SQLITE

    def test_default_proxy_mode(self):
        config = ScraperConfig()
        assert config.proxy_mode == ProxyMode.NONE

    def test_default_log_format(self):
        config = ScraperConfig()
        assert config.log_format == LogFormat.CONSOLE

    def test_default_retry_settings(self):
        config = ScraperConfig()
        assert config.retry_enabled is True
        assert config.max_retries == 3


class TestScraperConfigEnvVars:
    """Test configuration from environment variables."""

    def test_headless_from_env(self, monkeypatch):
        monkeypatch.setenv("XINGEST_HEADLESS", "false")
        config = ScraperConfig()
        assert config.headless is False

    def test_cache_backend_from_env(self, monkeypatch):
        monkeypatch.setenv("XINGEST_CACHE_BACKEND", "redis")
        config = ScraperConfig()
        assert config.cache_backend == CacheBackend.REDIS

    def test_proxy_mode_from_env(self, monkeypatch):
        monkeypatch.setenv("XINGEST_PROXY_MODE", "round_robin")
        config = ScraperConfig()
        assert config.proxy_mode == ProxyMode.ROUND_ROBIN

    def test_log_level_from_env(self, monkeypatch):
        monkeypatch.setenv("XINGEST_LOG_LEVEL", "DEBUG")
        config = ScraperConfig()
        assert config.log_level == "DEBUG"

    def test_cache_ttl_from_env(self, monkeypatch):
        monkeypatch.setenv("XINGEST_CACHE_TTL_SECONDS", "600")
        config = ScraperConfig()
        assert config.cache_ttl_seconds == 600


class TestProxyModeEnum:
    """Test ProxyMode enum values."""

    def test_proxy_modes(self):
        assert ProxyMode.ROUND_ROBIN.value == "round_robin"
        assert ProxyMode.RANDOM.value == "random"
        assert ProxyMode.NONE.value == "none"


class TestCacheBackendEnum:
    """Test CacheBackend enum values."""

    def test_cache_backends(self):
        assert CacheBackend.SQLITE.value == "sqlite"
        assert CacheBackend.REDIS.value == "redis"
        assert CacheBackend.NONE.value == "none"
