"""Tweet data model."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class TweetData(BaseModel):
    """Represents a scraped tweet."""

    tweet_id: str
    text: str
    created_at: datetime | None = None
    is_pinned: bool = False
    
    # Tweet type indicators
    is_reply: bool = False
    reply_to_username: str | None = None
    is_quote_tweet: bool = False
    quoted_tweet_id: str | None = None
    is_retweet: bool = False
    retweeted_from: str | None = None
    
    # Engagement metrics
    reply_count: int = 0
    repost_count: int = 0
    like_count: int = 0
    view_count: int | None = None
    media_urls: list[HttpUrl] | None = None
    tweet_url: HttpUrl
