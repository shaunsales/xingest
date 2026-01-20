"""Scrape result wrapper model."""

from datetime import datetime

from pydantic import BaseModel

from xingest.models.profile import ProfileData
from xingest.models.tweet import TweetData


class ScrapeResult(BaseModel):
    """Wrapper for complete scrape operation result."""

    success: bool
    username: str
    profile: ProfileData | None = None
    tweets: list[TweetData] = []
    cached: bool = False
    cache_age_seconds: float | None = None
    error_message: str | None = None
    scraped_at: datetime
    duration_ms: float
