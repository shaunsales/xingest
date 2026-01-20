# xingest

A Python library for scraping X/Twitter profile data using Playwright and BeautifulSoup.

## Features

- **Profile extraction**: Username, display name, bio, followers/following counts, verification status
- **Tweet extraction**: Text, timestamps, engagement metrics (likes, reposts, replies, views)
- **Pinned tweet detection**: Automatically identifies pinned tweets
- **Chronological ordering**: Tweets sorted newest-first (pinned tweets at top)
- **Caching**: SQLite or Redis caching with configurable TTL
- **Proxy support**: Round-robin or random proxy rotation
- **DataFrame export**: Convert results to pandas DataFrames or CSV
- **REST API**: Docker image with FastAPI + Swagger UI
- **Async-first**: Built on async/await for efficient concurrent scraping

## Installation

```bash
# Clone the repository
git clone https://github.com/shaunsales/xingest.git
cd xingest

# Install dependencies
pip install -e .

# Install Playwright browsers
playwright install chromium
```

## Quick Start

### Option 1: Docker (Recommended)

Get started in seconds with the pre-built Docker image:

```bash
# Clone and build
git clone https://github.com/shaunsales/xingest.git
cd xingest
docker build -t xingest .

# Run the API server
docker run -p 8000:8000 xingest

# Open Swagger UI
open http://localhost:8000/docs
```

Then scrape via the REST API:
```bash
curl "http://localhost:8000/api/scrape/elonmusk"
```

### Option 2: Python Library

```python
import asyncio
from xingest import Scraper

async def main():
    async with Scraper() as scraper:
        result = await scraper.scrape("elonmusk")
        print(f"Followers: {result.profile.followers_count:,}")
        for tweet in result.tweets[:3]:
            print(f"- {tweet.text[:50]}...")

asyncio.run(main())
```

### Option 3: CLI

```bash
# Scrape a profile
xingest scrape elonmusk

# Save to JSON
xingest scrape elonmusk -o elonmusk.json

# Batch scrape
xingest scrape elonmusk jack cz_binance
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
    website_url="https://tesla.com",
    followers_count=150000000,
    following_count=500,
    total_posts_count=25000,
    is_verified=True,
    joined_date=datetime(2009, 6, 1),
    scraped_at=datetime(2026, 1, 20, 12, 0, 0),
)
```

### TweetData
```python
TweetData(
    tweet_id="1234567890",
    text="Hello, world!",
    created_at=datetime(2026, 1, 15, 12, 0, 0),
    is_pinned=False,
    # Tweet type indicators
    is_reply=False,
    reply_to_username=None,
    is_quote_tweet=False,
    quoted_tweet_id=None,
    is_retweet=False,
    retweeted_from=None,
    # Engagement metrics
    like_count=1000,
    repost_count=100,
    reply_count=50,
    view_count=50000,
    media_urls=["https://pbs.twimg.com/media/..."],
    tweet_url="https://x.com/elonmusk/status/1234567890",
)
```

## DataFrame Export

Export results to pandas DataFrames for analysis:

```python
from xingest import Scraper, to_tweets_df, to_profile_df, save_csv

async with Scraper() as scraper:
    result = await scraper.scrape("elonmusk")
    
    # Convert to DataFrames
    tweets_df = to_tweets_df(result)
    profile_df = to_profile_df(result)
    
    # Save to CSV
    save_csv(result, "tweets.csv", tweets=True)
    save_csv(result, "profile.csv", tweets=False)
```

Install pandas support:
```bash
pip install xingest[pandas]
```

## REST API

The Docker image includes a FastAPI server with Swagger UI documentation.

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/scrape/{username}` | Quick scrape with query params |
| `POST` | `/api/scrape` | Scrape with full config options |
| `POST` | `/api/scrape/batch` | Batch scrape (up to 10 users) |
| `GET` | `/api/config` | View default configuration |

### Example POST Request

```bash
curl -X POST "http://localhost:8000/api/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "elonmusk",
    "options": {
      "force_refresh": false,
      "timeout_ms": 60000,
      "cache_enabled": true
    }
  }'
```

## Testing

```bash
# Run all unit tests (114 tests, no internet required)
pytest tests/ --ignore=tests/test_integration_scrape.py -v

# Run integration tests (requires internet, scrapes live data)
pytest tests/test_integration_scrape.py -v
```

## Project Structure

```
xingest/
├── xingest/
│   ├── core/           # Fetcher, parser, transformer, orchestrator, exporter
│   ├── models/         # Pydantic data models
│   ├── cache/          # SQLite and Redis cache implementations
│   ├── proxy/          # Proxy rotation
│   ├── logging/        # Structlog configuration
│   ├── api.py          # FastAPI REST server
│   ├── cli.py          # Typer CLI
│   └── config.py       # Pydantic Settings
├── tests/
│   ├── fixtures/       # Cached HTML/JSON for tests
│   └── test_*.py       # Unit tests (114 tests)
├── Dockerfile          # Docker build
└── docker-compose.yml  # Docker Compose config
```

## Optional Dependencies

```bash
pip install xingest[pandas]  # DataFrame/CSV export
pip install xingest[api]     # FastAPI server (included in Docker)
```

## License

MIT
