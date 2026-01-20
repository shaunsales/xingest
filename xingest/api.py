"""FastAPI web server for xingest scraper."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from xingest import Scraper, ScraperConfig, __version__
from xingest.config import CacheBackend
from xingest.core.exporter import to_dict


# Request/Response models
class ScrapeOptions(BaseModel):
    """Configuration options for scrape requests."""
    
    force_refresh: bool = Field(
        default=False,
        description="Skip cache and fetch fresh data",
    )
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode",
    )
    timeout_ms: int = Field(
        default=30000,
        ge=5000,
        le=120000,
        description="Browser timeout in milliseconds",
    )
    cache_enabled: bool = Field(
        default=True,
        description="Enable result caching",
    )
    cache_ttl_seconds: int = Field(
        default=300,
        ge=0,
        le=86400,
        description="Cache TTL in seconds",
    )


class ScrapeRequest(BaseModel):
    """Request body for single scrape."""
    
    username: str = Field(..., description="Twitter username to scrape")
    options: ScrapeOptions = Field(default_factory=ScrapeOptions)


class BatchScrapeRequest(BaseModel):
    """Request body for batch scrape."""
    
    usernames: list[str] = Field(..., min_length=1, max_length=10)
    options: ScrapeOptions = Field(default_factory=ScrapeOptions)
    delay_ms: int = Field(
        default=1000,
        ge=0,
        le=10000,
        description="Delay between requests in milliseconds",
    )


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    version: str
    timestamp: str


# Global scraper instance
_scraper: Optional[Scraper] = None


def _get_config(options: ScrapeOptions) -> ScraperConfig:
    """Create ScraperConfig from ScrapeOptions."""
    return ScraperConfig(
        headless=options.headless,
        browser_timeout_ms=options.timeout_ms,
        cache_backend=CacheBackend.SQLITE if options.cache_enabled else CacheBackend.NONE,
        cache_ttl_seconds=options.cache_ttl_seconds,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage scraper lifecycle."""
    global _scraper
    _scraper = Scraper(ScraperConfig())
    await _scraper.__aenter__()
    yield
    await _scraper.__aexit__(None, None, None)


# Create FastAPI app
app = FastAPI(
    title="xingest API",
    description="X/Twitter profile scraper API",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/scrape/{username}", tags=["Scraping"])
async def scrape_get(
    username: str,
    force_refresh: bool = Query(False, description="Skip cache"),
    headless: bool = Query(True, description="Headless browser mode"),
    timeout_ms: int = Query(30000, ge=5000, le=120000, description="Timeout in ms"),
):
    """
    Scrape a single X/Twitter profile.
    
    Simple GET endpoint for quick scraping with default options.
    """
    config = ScraperConfig(
        headless=headless,
        browser_timeout_ms=timeout_ms,
    )
    
    async with Scraper(config) as scraper:
        result = await scraper.scrape(username, force_refresh=force_refresh)
    
    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to scrape @{username}: {result.error_message}",
        )
    
    return to_dict(result)


@app.post("/api/scrape", tags=["Scraping"])
async def scrape_post(request: ScrapeRequest):
    """
    Scrape a single X/Twitter profile with full configuration options.
    
    Use this endpoint when you need fine-grained control over scraping behavior.
    """
    config = _get_config(request.options)
    
    async with Scraper(config) as scraper:
        result = await scraper.scrape(
            request.username,
            force_refresh=request.options.force_refresh,
        )
    
    if not result.success:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to scrape @{request.username}: {result.error_message}",
        )
    
    return to_dict(result)


@app.post("/api/scrape/batch", tags=["Scraping"])
async def scrape_batch(request: BatchScrapeRequest):
    """
    Scrape multiple X/Twitter profiles in sequence.
    
    Returns results for all requested profiles, including failures.
    Limited to 10 usernames per request.
    """
    config = _get_config(request.options)
    config.request_delay_ms = request.delay_ms
    
    async with Scraper(config) as scraper:
        results = await scraper.scrape_many(
            request.usernames,
            force_refresh=request.options.force_refresh,
        )
    
    return {
        "total": len(results),
        "successful": sum(1 for r in results if r.success),
        "failed": sum(1 for r in results if not r.success),
        "results": [to_dict(r) for r in results],
    }


@app.get("/api/config", tags=["System"])
async def get_default_config():
    """Get default scraper configuration."""
    config = ScraperConfig()
    return {
        "headless": config.headless,
        "browser_timeout_ms": config.browser_timeout_ms,
        "cache_backend": config.cache_backend.value,
        "cache_ttl_seconds": config.cache_ttl_seconds,
        "proxy_mode": config.proxy_mode.value,
        "max_concurrency": config.max_concurrency,
        "request_delay_ms": config.request_delay_ms,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
