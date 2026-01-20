"""Configuration management using Pydantic Settings."""

from enum import Enum

from pydantic_settings import BaseSettings


class ProxyMode(str, Enum):
    """Proxy selection strategy."""
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    NONE = "none"


class CacheBackend(str, Enum):
    """Cache backend type."""
    SQLITE = "sqlite"
    REDIS = "redis"
    NONE = "none"


class LogFormat(str, Enum):
    """Log output format."""
    JSON = "json"
    CONSOLE = "console"


class ScraperConfig(BaseSettings):
    """Configuration for the xingest scraper."""

    # Browser settings
    headless: bool = True
    browser_timeout_ms: int = 30000
    user_agent: str | None = None

    # Proxy settings
    proxy_mode: ProxyMode = ProxyMode.NONE
    proxy_urls: list[str] = []

    # Concurrency
    max_concurrency: int = 5
    request_delay_ms: int = 1000

    # Retry settings
    retry_enabled: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 2.0

    # Cache settings
    cache_backend: CacheBackend = CacheBackend.SQLITE
    cache_ttl_seconds: int = 300
    sqlite_path: str = ".xingest_cache.db"
    redis_url: str = "redis://localhost:6379/0"

    # Logging
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.CONSOLE

    model_config = {
        "env_prefix": "XINGEST_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }
