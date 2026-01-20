# Architecture Overview

## Data Flow

```
┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌──────────────┐
│   Fetcher   │───▶│   Parser    │───▶│ Transformer  │───▶│ ScrapeResult │
│ (Playwright)│    │(BeautifulSoup)│   │ (Pydantic)   │    │   (Output)   │
└─────────────┘    └─────────────┘    └──────────────┘    └──────────────┘
      │                                                           │
      ▼                                                           ▼
┌─────────────┐                                           ┌──────────────┐
│    Proxy    │                                           │    Cache     │
│  Provider   │                                           │   (SQLite)   │
└─────────────┘                                           └──────────────┘
```

## Core Modules

### `core/fetcher.py`
Playwright-based browser automation.

**Responsibilities:**
- Launch headless Chromium browser
- Navigate to X/Twitter profile pages
- Wait for dynamic content to load
- Return raw HTML

**Key function:** `fetch_profile_page(username, headless=True, proxy=None)`

### `core/parser.py`
BeautifulSoup HTML parsing with centralized selectors.

**Responsibilities:**
- Extract profile data (username, bio, counts)
- Extract tweet data (text, metrics, timestamps)
- Detect pinned tweets
- Report parse errors without failing

**Key functions:**
- `parse_page(html, username)` → `ParseResult`
- `parse_profile(soup)` → `dict`
- `parse_tweets(soup, username)` → `list[dict]`

### `core/transformer.py`
Data normalization and Pydantic model creation.

**Responsibilities:**
- Normalize count strings ("1.5M" → 1500000)
- Parse date strings (ISO, relative, absolute)
- Validate and create Pydantic models

**Key function:** `transform_result(parse_result, username)` → `ScrapeResult`

## Models

### `models/profile.py` - ProfileData
```python
class ProfileData(BaseModel):
    username: str
    display_name: str | None
    bio: str | None
    followers_count: int
    following_count: int
    is_verified: bool
    joined_date: datetime | None
    website_url: str | None
    profile_image_url: str | None
```

### `models/tweet.py` - TweetData
```python
class TweetData(BaseModel):
    tweet_id: str
    tweet_url: str | None
    text: str
    created_at: datetime | None
    like_count: int
    repost_count: int
    reply_count: int
    view_count: int
    is_pinned: bool
    media_urls: list[str]
```

### `models/result.py` - ScrapeResult
```python
class ScrapeResult(BaseModel):
    success: bool
    profile: ProfileData | None
    tweets: list[TweetData]
    scraped_at: datetime
    duration_ms: float
    cached: bool
    cache_age_seconds: float | None
```

## Infrastructure

### `config.py`
Pydantic Settings for configuration management.

- All settings via `XINGEST_*` environment variables
- `.env` file support
- Type-safe with enums for modes

### `cache/sqlite_cache.py`
Async SQLite caching with TTL.

- Stores serialized `ScrapeResult` JSON
- Automatic expiration handling
- Case-insensitive username lookup

### `proxy/rotating.py`
Proxy rotation with configurable strategies.

- Round-robin: Sequential cycling
- Random: Random selection each request
- Load from file support

### `logging/setup.py`
Structlog configuration.

- Console or JSON output
- Configurable log levels
- Context variable support

## Selector Strategy

All CSS selectors are centralized in `core/parser.py`:

```python
SELECTORS = {
    "user_name": '[data-testid="UserName"]',
    "user_description": '[data-testid="UserDescription"]',
    "tweet": '[data-testid="tweet"]',
    # ...
}
```

This makes selector updates easy when X/Twitter changes their markup.

## Error Handling

- `FetchError`: Browser/network issues
- `ParseError`: HTML parsing failures  
- `RateLimitError`: Rate limiting detected
- `AuthenticationError`: Login required

All errors inherit from `XingestError` base class.
