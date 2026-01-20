# PLAN.md — X/Twitter Profile & Tweet Scraper

## Overview

A Python library and CLI tool for scraping public profile information and recent tweets from X/Twitter accounts without requiring API access or authentication. Designed for monitoring a small number of accounts for their latest public content.

### Goals
- Retrieve profile metadata and recent tweets from public X/Twitter profiles
- Operate without X API access or user authentication
- Provide both CLI and programmatic (library) interfaces
- Support concurrent scraping of multiple accounts
- Evade bot detection via proxy rotation and browser emulation

---

## Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Language | Python 3.12+ | Latest features, improved performance |
| Browser Automation | Playwright (async) | Modern, fast, excellent async support |
| HTML Parsing | BeautifulSoup4 + lxml | Requirement specified, lxml for speed |
| Data Validation | Pydantic v2 | Fast validation, JSON serialization |
| HTTP Client | httpx (if needed) | Async-native, modern |
| Caching - Local | SQLite via aiosqlite | Zero-config, portable |
| Caching - Distributed | Redis via redis-py | Industry standard |
| Logging | structlog | Structured logging, sink flexibility |
| CLI | Typer | Modern, type-hint based CLI |
| Retry Logic | tenacity | Flexible retry strategies |
| Concurrency | asyncio + semaphores | Native async, controlled parallelism |

---

## Architecture

```
xingest/
├── __init__.py              # Public API exports
├── __main__.py              # CLI entry point
├── cli.py                   # Typer CLI definitions
├── config.py                # Configuration management
├── core/
│   ├── __init__.py
│   ├── orchestrator.py      # Pipeline coordinator, concurrency
│   ├── fetcher.py           # Playwright browser automation
│   ├── parser.py            # BeautifulSoup HTML extraction
│   ├── transformer.py       # Raw data → validated models
│   └── exporter.py          # JSON output generation
├── models/
│   ├── __init__.py
│   ├── profile.py           # ProfileData Pydantic model
│   ├── tweet.py             # TweetData Pydantic model
│   └── result.py            # ScrapeResult wrapper model
├── cache/
│   ├── __init__.py
│   ├── base.py              # Abstract cache interface
│   ├── sqlite_cache.py      # SQLite implementation
│   └── redis_cache.py       # Redis implementation
├── logging/
│   ├── __init__.py
│   └── setup.py             # structlog configuration, sinks
├── proxy/
│   ├── __init__.py
│   ├── base.py              # Abstract proxy provider
│   └── rotating.py          # Round-robin / random proxy selector
└── exceptions.py            # Custom exception hierarchy
```

### Data Flow Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CONFIG    │     │    CACHE    │     │   FETCHER   │     │   PARSER    │
│             │     │   CHECK     │     │ (Playwright)│     │(BeautifulSoup)
│ - username  │────▶│             │────▶│             │────▶│             │
│ - proxy     │     │ HIT? ──────────────────────────────┐  │ - extract   │
│ - options   │     │ MISS? ─────▶│ render page │        │  │   profile   │
└─────────────┘     └─────────────┘     └─────────────┘  │  │ - extract   │
                                                         │  │   tweets    │
                                                         │  └──────┬──────┘
                                                         │         │
┌─────────────┐     ┌─────────────┐     ┌─────────────┐  │         │
│   OUTPUT    │◀────│   EXPORTER  │◀────│ TRANSFORMER │◀─┴─────────┘
│             │     │             │     │             │
│ - JSON file │     │ - serialize │     │ - validate  │
│ - stdout    │     │ - format    │     │ - Pydantic  │
│ - return    │     │             │     │ - normalize │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Data Models

### ProfileData

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class ProfileData(BaseModel):
    username: str                          # @handle without @
    display_name: str
    bio: str | None
    website_url: HttpUrl | None
    joined_date: datetime | None           # Parse "Joined March 2009"
    followers_count: int
    following_count: int
    total_posts_count: int
    is_verified: bool
    scraped_at: datetime                   # When we fetched this
```

### TweetData

```python
from pydantic import BaseModel, HttpUrl
from datetime import datetime

class TweetData(BaseModel):
    tweet_id: str                          # Extracted from URL/data attr
    text: str
    created_at: datetime | None
    is_pinned: bool                        # True if pinned tweet
    reply_count: int
    repost_count: int
    like_count: int
    view_count: int | None                 # Sometimes unavailable
    media_urls: list[HttpUrl] | None       # Optional, empty list if none
    tweet_url: HttpUrl                     # Direct link to tweet
```

### ScrapeResult

```python
from pydantic import BaseModel
from datetime import datetime

class ScrapeResult(BaseModel):
    success: bool
    username: str
    profile: ProfileData | None
    tweets: list[TweetData]
    cached: bool                           # True if served from cache
    cache_age_seconds: float | None        # How old the cached data is
    error_message: str | None
    scraped_at: datetime
    duration_ms: float                     # Time taken to scrape
```

---

## Module Specifications

### config.py

Centralized configuration using Pydantic Settings for env var support.

```python
from pydantic_settings import BaseSettings
from enum import Enum

class ProxyMode(str, Enum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    NONE = "none"

class CacheBackend(str, Enum):
    SQLITE = "sqlite"
    REDIS = "redis"
    NONE = "none"

class ScraperConfig(BaseSettings):
    # Browser settings
    user_agents: list[str]                 # Pool of user agents to rotate
    headless: bool = True
    browser_timeout_ms: int = 30000
    
    # Proxy settings
    proxy_mode: ProxyMode = ProxyMode.NONE
    proxy_urls: list[str] = []             # List of proxy URLs
    
    # Concurrency
    max_concurrency: int = 5
    request_delay_ms: int = 1000           # Delay between requests
    
    # Retry settings
    retry_enabled: bool = True
    max_retries: int = 3
    retry_backoff_base: float = 2.0
    
    # Cache settings
    cache_backend: CacheBackend = CacheBackend.SQLITE
    cache_ttl_seconds: int = 300           # 5 minutes default
    sqlite_path: str = ".xingest_cache.db"
    redis_url: str = "redis://localhost:6379/0"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"               # "json" or "console"
    log_sink_url: str | None = None        # e.g., Seq endpoint
    
    class Config:
        env_prefix = "XINGEST_"
```

### core/fetcher.py

Handles Playwright browser automation with proxy and user-agent rotation.

**Responsibilities:**
- Launch headless browser with randomized fingerprint
- Configure proxy per request
- Navigate to profile URL
- Wait for content to load (specific selectors)
- Return rendered HTML
- Handle page-level errors (timeout, blocked, etc.)

**Key Functions:**
```python
async def fetch_profile_page(
    username: str,
    config: ScraperConfig,
    proxy_provider: ProxyProvider | None
) -> FetchResult:
    """
    Returns FetchResult containing:
    - html: str (rendered page HTML)
    - success: bool
    - error: str | None
    - response_status: int | None
    """
```

**Implementation Notes:**
- Use `playwright.async_api`
- Create new browser context per request (isolation)
- Set viewport to common desktop resolution
- Wait for `[data-testid="primaryColumn"]` to appear
- Additional wait for tweet elements: `[data-testid="tweet"]`
- Capture console errors for debugging
- Screenshot on failure (optional, for debugging)

### core/parser.py

Extracts raw data from HTML using BeautifulSoup.

**Responsibilities:**
- Parse HTML with BeautifulSoup + lxml
- Extract profile section data
- Extract tweet elements
- Identify pinned tweet (first tweet with pin indicator)
- Return raw dictionaries (not yet validated)

**Key Functions:**
```python
def parse_profile(soup: BeautifulSoup) -> dict:
    """Extract profile metadata as raw dict."""

def parse_tweets(soup: BeautifulSoup) -> list[dict]:
    """Extract all tweet data as list of raw dicts."""

def parse_page(html: str) -> ParseResult:
    """
    Full page parsing, returns ParseResult containing:
    - profile_data: dict
    - tweets_data: list[dict]
    - parse_errors: list[str]  # Non-fatal issues
    """
```

**Implementation Notes:**
- Profile selectors (these WILL change, encapsulate for easy updates):
  - Bio: `[data-testid="UserDescription"]`
  - Stats: `a[href*="/followers"]`, `a[href*="/following"]`
  - Join date: `[data-testid="UserJoinDate"]`
  - Website: `[data-testid="UserUrl"]`
- Tweet selectors:
  - Container: `[data-testid="tweet"]`
  - Text: `[data-testid="tweetText"]`
  - Metrics: `[data-testid="reply"]`, `[data-testid="retweet"]`, `[data-testid="like"]`
  - Pinned indicator: Contains "Pinned" text in ancestor elements
- Use defensive extraction (try/except per field)
- Log warnings for missing expected elements

### core/transformer.py

Validates and normalizes raw parsed data into Pydantic models.

**Responsibilities:**
- Convert raw dicts to Pydantic models
- Parse date strings to datetime objects
- Normalize count strings ("1.2K" → 1200, "1M" → 1000000)
- Handle missing/malformed data gracefully
- Add metadata (scraped_at, etc.)

**Key Functions:**
```python
def normalize_count(count_str: str) -> int:
    """Convert '1.2K', '1M', '500' to integers."""

def parse_relative_date(date_str: str) -> datetime | None:
    """Convert 'Mar 15', '2h', 'Jan 5, 2024' to datetime."""

def transform_profile(raw: dict, username: str) -> ProfileData:
    """Transform raw profile dict to validated model."""

def transform_tweets(raw_tweets: list[dict], username: str) -> list[TweetData]:
    """Transform raw tweet dicts to validated models."""

def transform_result(
    parse_result: ParseResult,
    username: str,
    cached: bool,
    duration_ms: float
) -> ScrapeResult:
    """Create final ScrapeResult from parsed data."""
```

### core/exporter.py

Handles JSON output serialization.

**Responsibilities:**
- Serialize ScrapeResult to JSON
- Support output to file or stdout
- Pretty-print option
- Handle datetime serialization

**Key Functions:**
```python
def export_json(
    result: ScrapeResult,
    output_path: Path | None = None,
    pretty: bool = True
) -> str:
    """
    Export to JSON. Returns JSON string.
    If output_path provided, also writes to file.
    """

def export_batch_json(
    results: list[ScrapeResult],
    output_path: Path | None = None,
    pretty: bool = True
) -> str:
    """Export multiple results as JSON array."""
```

### core/orchestrator.py

Coordinates the full pipeline with concurrency control.

**Responsibilities:**
- Manage async execution
- Enforce concurrency limits (semaphore)
- Handle cache check/store
- Coordinate proxy rotation
- Aggregate results
- Emit structured logs

**Key Functions:**
```python
class Orchestrator:
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.cache = self._init_cache()
        self.proxy_provider = self._init_proxy()
        self.semaphore = asyncio.Semaphore(config.max_concurrency)
    
    async def scrape_profile(self, username: str) -> ScrapeResult:
        """Scrape a single profile with caching."""
    
    async def scrape_profiles(
        self, 
        usernames: list[str]
    ) -> list[ScrapeResult]:
        """Scrape multiple profiles concurrently."""
    
    async def __aenter__(self):
        """Async context manager - init browser."""
    
    async def __aexit__(self, *args):
        """Cleanup browser resources."""
```

**Execution Flow:**
```python
async def scrape_profile(self, username: str) -> ScrapeResult:
    async with self.semaphore:  # Concurrency control
        # 1. Check cache
        cached = await self.cache.get(username)
        if cached and not cached.is_expired:
            return cached.with_metadata(cached=True)
        
        # 2. Fetch with retry
        start = time.monotonic()
        fetch_result = await self._fetch_with_retry(username)
        if not fetch_result.success:
            return ScrapeResult(success=False, error=fetch_result.error, ...)
        
        # 3. Parse
        parse_result = parse_page(fetch_result.html)
        
        # 4. Transform
        result = transform_result(parse_result, username, ...)
        
        # 5. Cache store
        await self.cache.set(username, result)
        
        # 6. Return
        result.duration_ms = (time.monotonic() - start) * 1000
        return result
```

### cache/base.py

Abstract interface for cache implementations.

```python
from abc import ABC, abstractmethod

class CacheProvider(ABC):
    @abstractmethod
    async def get(self, username: str) -> ScrapeResult | None:
        """Retrieve cached result, None if miss or expired."""
    
    @abstractmethod
    async def set(self, username: str, result: ScrapeResult) -> None:
        """Store result in cache."""
    
    @abstractmethod
    async def invalidate(self, username: str) -> None:
        """Remove specific entry."""
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached entries."""
    
    @abstractmethod
    async def close(self) -> None:
        """Cleanup connections."""
```

### cache/sqlite_cache.py

SQLite-based local cache using aiosqlite.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS cache (
    username TEXT PRIMARY KEY,
    result_json TEXT NOT NULL,
    created_at REAL NOT NULL,  -- Unix timestamp
    expires_at REAL NOT NULL   -- Unix timestamp
);

CREATE INDEX IF NOT EXISTS idx_expires ON cache(expires_at);
```

### cache/redis_cache.py

Redis-based distributed cache.

**Key format:** `xingest:{username}`
**Storage:** JSON string with TTL set via SETEX

### proxy/rotating.py

Manages proxy rotation with multiple selection strategies.

```python
class ProxyProvider:
    def __init__(
        self, 
        proxy_urls: list[str], 
        mode: ProxyMode
    ):
        self.proxies = proxy_urls
        self.mode = mode
        self._index = 0
        self._lock = asyncio.Lock()
    
    async def get_next(self) -> str | None:
        """Get next proxy URL based on mode."""
        if not self.proxies:
            return None
        
        async with self._lock:
            if self.mode == ProxyMode.ROUND_ROBIN:
                proxy = self.proxies[self._index % len(self.proxies)]
                self._index += 1
            else:  # RANDOM
                proxy = random.choice(self.proxies)
        
        return proxy
```

### logging/setup.py

Configures structlog with multiple sink support.

```python
import structlog
import httpx

def configure_logging(config: ScraperConfig) -> None:
    """Configure structlog with appropriate processors and sinks."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    
    if config.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, config.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

# Optional: Seq sink as custom processor
class SeqSink:
    def __init__(self, seq_url: str):
        self.client = httpx.AsyncClient()
        self.url = f"{seq_url}/api/events/raw"
    
    async def send(self, event: dict) -> None:
        await self.client.post(self.url, json=event)
```

### cli.py

Typer-based CLI with full feature access.

```python
import typer
from pathlib import Path

app = typer.Typer(
    name="xingest",
    help="Scrape X/Twitter profiles and tweets"
)

@app.command()
def scrape(
    usernames: list[str] = typer.Argument(..., help="Usernames to scrape"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Output JSON file"),
    concurrency: int = typer.Option(5, "-c", "--concurrency", help="Max concurrent requests"),
    cache_ttl: int = typer.Option(300, "--cache-ttl", help="Cache TTL in seconds"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass cache"),
    proxy_file: Path | None = typer.Option(None, "--proxy-file", help="File with proxy URLs"),
    proxy_mode: str = typer.Option("random", "--proxy-mode", help="random or round_robin"),
    pretty: bool = typer.Option(True, "--pretty/--compact", help="Pretty print JSON"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose logging"),
):
    """Scrape one or more X/Twitter profiles."""
    ...

@app.command()
def clear_cache(
    sqlite_path: Path = typer.Option(".xingest_cache.db", help="SQLite cache path"),
):
    """Clear the local cache."""
    ...

@app.command()
def version():
    """Show version information."""
    ...

if __name__ == "__main__":
    app()
```

**CLI Examples:**
```bash
# Single profile
xingest scrape elonmusk -o result.json

# Multiple profiles with concurrency
xingest scrape elonmusk openai anthropic -c 3 -o results.json

# With proxy file
xingest scrape elonmusk --proxy-file proxies.txt --proxy-mode round_robin

# Bypass cache
xingest scrape elonmusk --no-cache

# Compact JSON output to stdout
xingest scrape elonmusk --compact
```

### __init__.py — Public API

```python
from xingest.core.orchestrator import Orchestrator
from xingest.config import ScraperConfig
from xingest.models import ProfileData, TweetData, ScrapeResult

__all__ = [
    "Orchestrator",
    "ScraperConfig", 
    "ProfileData",
    "TweetData",
    "ScrapeResult",
    "scrape",          # Convenience function
    "scrape_async",    # Async convenience function
]

def scrape(usernames: list[str], **config_kwargs) -> list[ScrapeResult]:
    """Synchronous convenience function."""
    import asyncio
    return asyncio.run(scrape_async(usernames, **config_kwargs))

async def scrape_async(
    usernames: list[str], 
    **config_kwargs
) -> list[ScrapeResult]:
    """Async convenience function."""
    config = ScraperConfig(**config_kwargs)
    async with Orchestrator(config) as orchestrator:
        return await orchestrator.scrape_profiles(usernames)
```

**Usage as Library:**
```python
from xingest import scrape, ScraperConfig

# Simple usage
results = scrape(["elonmusk", "openai"])

# With configuration
results = scrape(
    ["elonmusk"],
    proxy_urls=["http://proxy1:8080", "http://proxy2:8080"],
    proxy_mode="round_robin",
    cache_ttl_seconds=600,
    max_concurrency=3,
)

# Async usage
import asyncio
from xingest import Orchestrator, ScraperConfig

async def main():
    config = ScraperConfig(max_concurrency=5)
    async with Orchestrator(config) as orch:
        results = await orch.scrape_profiles(["elonmusk", "openai"])
        for r in results:
            print(r.model_dump_json(indent=2))

asyncio.run(main())
```

---

## Error Handling Strategy

### Exception Hierarchy

```python
class XScraperError(Exception):
    """Base exception for all scraper errors."""

class FetchError(XScraperError):
    """Failed to fetch page."""

class PageBlockedError(FetchError):
    """Detected bot blocking or rate limit."""

class ProfileNotFoundError(FetchError):
    """Profile does not exist or is suspended."""

class ParseError(XScraperError):
    """Failed to parse page content."""

class CacheError(XScraperError):
    """Cache operation failed."""

class ConfigError(XScraperError):
    """Invalid configuration."""
```

### Fail-Fast Behavior

- On FetchError: Log error, return ScrapeResult with `success=False`
- On ParseError: Log error, return partial result if possible
- On CacheError: Log warning, continue without cache
- Retry is attempted only for FetchError (configurable)

### Retry Logic

```python
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential,
    retry_if_exception_type
)

@retry(
    retry=retry_if_exception_type(FetchError),
    stop=stop_after_attempt(config.max_retries),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    before_sleep=lambda retry_state: log.warning(
        "retry_attempt",
        attempt=retry_state.attempt_number,
        wait=retry_state.next_action.sleep
    )
)
async def fetch_with_retry(username: str) -> FetchResult:
    ...
```

---

## Testing Strategy

### Unit Tests

| Module | Test Focus |
|--------|------------|
| `parser.py` | Static HTML fixtures, selector accuracy |
| `transformer.py` | Count normalization, date parsing, edge cases |
| `exporter.py` | JSON serialization, file output |
| `proxy/rotating.py` | Rotation logic, thread safety |
| `cache/*` | Set/get/expire/invalidate operations |

### Integration Tests

- Full pipeline with mocked Playwright
- Cache integration (SQLite)
- CLI smoke tests

### Test Fixtures

Maintain saved HTML snapshots of X/Twitter pages for:
- Regular profile with tweets
- Profile with pinned tweet
- Private/suspended profile
- Profile with no tweets

**Location:** `tests/fixtures/`

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=xingest --cov-report=html

# Specific module
pytest tests/test_parser.py -v
```

---

## Project Setup

### pyproject.toml

```toml
[project]
name = "xingest"
version = "0.1.0"
description = "X/Twitter profile and tweet scraper"
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.40.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "httpx>=0.25.0",
    "aiosqlite>=0.19.0",
    "redis>=5.0.0",
    "structlog>=23.2.0",
    "typer>=0.9.0",
    "tenacity>=8.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
xingest = "xingest.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Post-Install

```bash
# Install Playwright browsers
playwright install chromium
```

