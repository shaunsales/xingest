# xingest

A Python library for scraping X/Twitter profile data using Playwright and BeautifulSoup.

## Features

- **Profile extraction**: Username, display name, bio, followers/following counts, verification status
- **Tweet extraction**: Text, timestamps, engagement metrics (likes, reposts, replies, views)
- **Pinned tweet detection**: Automatically identifies pinned tweets
- **Caching**: SQLite-based caching with configurable TTL
- **Proxy support**: Round-robin or random proxy rotation
- **Async-first**: Built on async/await for efficient concurrent scraping

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/xingest.git
cd xingest

# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## Quick Start

```python
import asyncio
from xingest.core.fetcher import fetch_profile_page
from xingest.core.parser import parse_page
from xingest.core.transformer import transform_result

async def scrape_profile(username: str):
    # Fetch HTML
    result = await fetch_profile_page(username, headless=True)
    if not result.success:
        print(f"Error: {result.error}")
        return None
    
    # Parse and transform
    parsed = parse_page(result.html, username)
    return transform_result(parsed, username)

# Run
result = asyncio.run(scrape_profile("elonmusk"))
print(f"Followers: {result.profile.followers_count:,}")
for tweet in result.tweets[:3]:
    print(f"- {tweet.text[:50]}... ({tweet.like_count:,} likes)")
```

## Configuration

All settings can be configured via environment variables (prefix: `XINGEST_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `XINGEST_HEADLESS` | `true` | Run browser in headless mode |
| `XINGEST_CACHE_BACKEND` | `sqlite` | Cache backend (`sqlite`, `redis`, `none`) |
| `XINGEST_CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `XINGEST_PROXY_MODE` | `none` | Proxy mode (`none`, `round_robin`, `random`) |
| `XINGEST_LOG_LEVEL` | `INFO` | Log level |
| `XINGEST_LOG_FORMAT` | `console` | Log format (`console`, `json`) |

Or use a `.env` file in your project root.

## Data Models

### ProfileData
```python
ProfileData(
    username="elonmusk",
    display_name="Elon Musk",
    bio="...",
    followers_count=150000000,
    following_count=500,
    is_verified=True,
    joined_date=datetime(2009, 6, 1),
)
```

### TweetData
```python
TweetData(
    tweet_id="1234567890",
    text="Hello, world!",
    created_at=datetime(2024, 1, 15, 12, 0, 0),
    like_count=1000,
    repost_count=100,
    reply_count=50,
    view_count=50000,
    is_pinned=False,
)
```

## Testing

```bash
# Run unit tests (no internet required, uses cached fixtures)
pytest tests/test_parser.py tests/test_config.py tests/test_cache.py tests/test_proxy.py -v

# Run integration tests (requires internet, scrapes live data)
python tests/test_integration_scrape.py
```

## Project Structure

```
xingest/
├── xingest/
│   ├── core/           # Fetcher, parser, transformer
│   ├── models/         # Pydantic data models
│   ├── cache/          # Cache implementations
│   ├── proxy/          # Proxy rotation
│   ├── logging/        # Structlog configuration
│   └── config.py       # Pydantic Settings
├── tests/
│   ├── fixtures/       # Cached HTML/JSON for tests
│   └── test_*.py       # Unit tests
└── scripts/            # Utility scripts
```

## License

MIT
