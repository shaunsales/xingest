"""Profile data model."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class ProfileData(BaseModel):
    """Represents scraped X/Twitter profile metadata."""

    username: str
    display_name: str
    bio: str | None = None
    website_url: HttpUrl | None = None
    joined_date: datetime | None = None
    followers_count: int
    following_count: int
    total_posts_count: int
    is_verified: bool = False
    scraped_at: datetime
