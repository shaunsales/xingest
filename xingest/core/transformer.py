"""Data transformation and normalization for scraped data."""

import re
from datetime import datetime

from xingest.models.profile import ProfileData
from xingest.models.tweet import TweetData
from xingest.models.result import ScrapeResult
from xingest.core.parser import ParseResult


def normalize_count(count_str: str | None) -> int:
    """
    Convert count strings to integers.

    Examples:
        "1.2K" -> 1200
        "1M" -> 1000000
        "500" -> 500
        "1,234" -> 1234
    """
    if not count_str:
        return 0

    count_str = count_str.strip().upper().replace(",", "")

    if not count_str:
        return 0

    multipliers = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
    }

    for suffix, multiplier in multipliers.items():
        if count_str.endswith(suffix):
            try:
                number = float(count_str[:-1])
                return int(number * multiplier)
            except ValueError:
                return 0

    try:
        return int(float(count_str))
    except ValueError:
        return 0


def parse_joined_date(date_str: str | None) -> datetime | None:
    """
    Parse X/Twitter join date string.

    Examples:
        "Joined March 2009" -> datetime(2009, 3, 1)
        "Joined September 2021" -> datetime(2021, 9, 1)
    """
    if not date_str:
        return None

    # Remove "Joined " prefix
    date_str = date_str.replace("Joined ", "").strip()

    # Try parsing "Month Year" format
    try:
        return datetime.strptime(date_str, "%B %Y")
    except ValueError:
        pass

    # Try "Mon Year" abbreviated format
    try:
        return datetime.strptime(date_str, "%b %Y")
    except ValueError:
        pass

    return None


def parse_tweet_date(date_str: str | None) -> datetime | None:
    """
    Parse tweet date/time strings.

    X/Twitter uses various formats:
        - ISO 8601: "2026-01-18T18:17:20.000Z"
        - "2h" (relative)
        - "Mar 15" (same year)
        - "Jan 5, 2024" (different year)
    """
    if not date_str:
        return None

    date_str = date_str.strip()
    now = datetime.now()

    # ISO 8601 format (from <time datetime="..."> element)
    if "T" in date_str and (date_str.endswith("Z") or "+" in date_str):
        try:
            # Handle "2026-01-18T18:17:20.000Z" format
            clean = date_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean)
        except ValueError:
            pass

    # Relative time patterns
    relative_patterns = [
        (r"(\d+)s$", "seconds"),
        (r"(\d+)m$", "minutes"),
        (r"(\d+)h$", "hours"),
        (r"(\d+)d$", "days"),
    ]

    for pattern, unit in relative_patterns:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if unit == "seconds":
                return now.replace(microsecond=0)
            elif unit == "minutes":
                from datetime import timedelta
                return now - timedelta(minutes=value)
            elif unit == "hours":
                from datetime import timedelta
                return now - timedelta(hours=value)
            elif unit == "days":
                from datetime import timedelta
                return now - timedelta(days=value)

    # "Month Day, Year" format
    try:
        return datetime.strptime(date_str, "%b %d, %Y")
    except ValueError:
        pass

    # "Month Day" (current year)
    try:
        parsed = datetime.strptime(date_str, "%b %d")
        return parsed.replace(year=now.year)
    except ValueError:
        pass

    return None


def transform_profile(raw: dict, username: str) -> ProfileData:
    """
    Transform raw profile dict to validated ProfileData model.

    Args:
        raw: Raw profile data from parser
        username: Fallback username if not parsed

    Returns:
        Validated ProfileData model
    """
    return ProfileData(
        username=raw.get("username", username),
        display_name=raw.get("display_name", username),
        bio=raw.get("bio"),
        website_url=raw.get("website_url"),
        joined_date=parse_joined_date(raw.get("joined_date_raw")),
        followers_count=normalize_count(raw.get("followers_count_raw")),
        following_count=normalize_count(raw.get("following_count_raw")),
        total_posts_count=normalize_count(raw.get("posts_count_raw", "0")),
        is_verified=raw.get("is_verified", False),
        scraped_at=datetime.now(),
    )


def transform_tweets(raw_tweets: list[dict], username: str) -> list[TweetData]:
    """
    Transform raw tweet dicts to validated TweetData models.

    Args:
        raw_tweets: List of raw tweet data from parser
        username: Profile username for URL construction

    Returns:
        List of validated TweetData models
    """
    tweets = []

    for raw in raw_tweets:
        tweet_id = raw.get("tweet_id")
        if not tweet_id:
            continue

        tweet_url = raw.get("tweet_url", f"https://x.com/{username}/status/{tweet_id}")

        tweet = TweetData(
            tweet_id=tweet_id,
            text=raw.get("text", ""),
            created_at=parse_tweet_date(raw.get("created_at_raw")),
            is_pinned=raw.get("is_pinned", False),
            reply_count=normalize_count(raw.get("reply_count_raw")),
            repost_count=normalize_count(raw.get("repost_count_raw")),
            like_count=normalize_count(raw.get("like_count_raw")),
            view_count=normalize_count(raw.get("view_count_raw")) or None,
            media_urls=raw.get("media_urls"),
            tweet_url=tweet_url,
        )
        tweets.append(tweet)

    return tweets


def transform_result(
    parse_result: ParseResult,
    username: str,
    cached: bool = False,
    cache_age_seconds: float | None = None,
    duration_ms: float = 0.0,
) -> ScrapeResult:
    """
    Create final ScrapeResult from parsed data.

    Args:
        parse_result: ParseResult from parser
        username: Profile username
        cached: Whether data was served from cache
        cache_age_seconds: Age of cached data
        duration_ms: Time taken to scrape

    Returns:
        Complete ScrapeResult model
    """
    profile = None
    tweets = []
    success = True
    error_message = None

    try:
        if parse_result.profile_data:
            profile = transform_profile(parse_result.profile_data, username)
    except Exception as e:
        success = False
        error_message = f"Profile transform error: {e}"

    try:
        if parse_result.tweets_data:
            tweets = transform_tweets(parse_result.tweets_data, username)
    except Exception as e:
        if not error_message:
            error_message = f"Tweets transform error: {e}"

    # Include parse errors
    if parse_result.parse_errors:
        if error_message:
            error_message += "; " + "; ".join(parse_result.parse_errors)
        else:
            error_message = "; ".join(parse_result.parse_errors)

    return ScrapeResult(
        success=success and profile is not None,
        username=username,
        profile=profile,
        tweets=tweets,
        cached=cached,
        cache_age_seconds=cache_age_seconds,
        error_message=error_message,
        scraped_at=datetime.now(),
        duration_ms=duration_ms,
    )
