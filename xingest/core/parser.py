"""BeautifulSoup-based HTML parser for X/Twitter profiles."""

from dataclasses import dataclass, field

from bs4 import BeautifulSoup


@dataclass
class ParseResult:
    """Result of parsing a profile page."""

    profile_data: dict
    tweets_data: list[dict]
    parse_errors: list[str] = field(default_factory=list)


# Selectors - centralized for easy updates when X changes their DOM
SELECTORS = {
    "primary_column": '[data-testid="primaryColumn"]',
    "user_name": '[data-testid="UserName"]',
    "user_description": '[data-testid="UserDescription"]',
    "user_join_date": '[data-testid="UserJoinDate"]',
    "user_url": '[data-testid="UserUrl"]',
    "user_location": '[data-testid="UserLocation"]',
    "followers_link": 'a[href$="/verified_followers"]',
    "following_link": 'a[href$="/following"]',
    "tweet": '[data-testid="tweet"]',
    "tweet_text": '[data-testid="tweetText"]',
    "reply_button": '[data-testid="reply"]',
    "retweet_button": '[data-testid="retweet"]',
    "like_button": '[data-testid="like"]',
    "views": 'a[href*="/analytics"]',
}


def parse_profile(soup: BeautifulSoup) -> dict:
    """
    Extract profile metadata from parsed HTML.

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        Dict with raw profile data (not yet validated)
    """
    profile = {}

    # Username and display name from UserName element
    user_name_el = soup.select_one(SELECTORS["user_name"])
    if user_name_el:
        spans = user_name_el.find_all("span", recursive=True)
        # Display name is usually in the first substantial span (not starting with @)
        for span in spans:
            text = span.get_text(strip=True)
            if text and not text.startswith("@"):
                profile["display_name"] = text
                break
        # Username is the @handle
        for span in spans:
            text = span.get_text(strip=True)
            if text.startswith("@"):
                profile["username"] = text[1:]  # Remove @
                break
        # Fallback: if no display_name found, use username
        if "username" in profile and "display_name" not in profile:
            profile["display_name"] = profile["username"]

    # Bio/description
    bio_el = soup.select_one(SELECTORS["user_description"])
    if bio_el:
        profile["bio"] = bio_el.get_text(strip=True)

    # Join date
    join_date_el = soup.select_one(SELECTORS["user_join_date"])
    if join_date_el:
        profile["joined_date_raw"] = join_date_el.get_text(strip=True)

    # Website URL
    url_el = soup.select_one(SELECTORS["user_url"])
    if url_el:
        link = url_el.find("a")
        if link and link.get("href"):
            profile["website_url"] = link.get("href")

    # Follower/following counts
    followers_el = soup.select_one(SELECTORS["followers_link"])
    if followers_el:
        span = followers_el.find("span")
        if span:
            profile["followers_count_raw"] = span.get_text(strip=True)

    following_el = soup.select_one(SELECTORS["following_link"])
    if following_el:
        span = following_el.find("span")
        if span:
            profile["following_count_raw"] = span.get_text(strip=True)

    # Check for verification badge
    profile["is_verified"] = bool(soup.select_one('[data-testid="icon-verified"]'))

    return profile


def _find_pinned_tweet_id(soup: BeautifulSoup) -> str | None:
    """Find the tweet ID of the pinned tweet, if any."""
    # Find elements containing exactly "Pinned" text
    pinned_elements = soup.find_all(string=lambda t: t and t.strip() == "Pinned")
    
    for pinned_text in pinned_elements:
        # Walk up to find the containing element that also has a tweet
        parent = pinned_text.parent
        for _ in range(20):
            if parent is None:
                break
            # Look for a tweet within this container
            tweet_el = parent.find(attrs={"data-testid": "tweet"})
            if tweet_el:
                # Extract tweet ID
                links = tweet_el.select('a[href*="/status/"]')
                for link in links:
                    href = link.get("href", "")
                    if "/status/" in href:
                        tweet_id = href.split("/status/")[1].split("/")[0].split("?")[0]
                        if tweet_id.isdigit():
                            return tweet_id
                break
            parent = parent.parent
    
    return None


def parse_tweets(soup: BeautifulSoup, username: str | None = None) -> list[dict]:
    """
    Extract tweet data from parsed HTML.

    Args:
        soup: BeautifulSoup object of the page
        username: Profile username to construct tweet URLs

    Returns:
        List of dicts with raw tweet data (not yet validated)
    """
    # First, find the pinned tweet ID (if any)
    pinned_tweet_id = _find_pinned_tweet_id(soup)
    
    tweets = []
    tweet_elements = soup.select(SELECTORS["tweet"])

    for i, tweet_el in enumerate(tweet_elements):
        tweet = {}

        # Tweet text
        text_el = tweet_el.select_one(SELECTORS["tweet_text"])
        if text_el:
            tweet["text"] = text_el.get_text(strip=True)
        else:
            tweet["text"] = ""

        # Extract tweet ID from links
        tweet_links = tweet_el.select('a[href*="/status/"]')
        for link in tweet_links:
            href = link.get("href", "")
            if "/status/" in href:
                parts = href.split("/status/")
                if len(parts) > 1:
                    tweet_id = parts[1].split("/")[0].split("?")[0]
                    if tweet_id.isdigit():
                        tweet["tweet_id"] = tweet_id
                        tweet["tweet_url"] = f"https://x.com{href.split('?')[0]}"
                        # Check if this is the pinned tweet
                        tweet["is_pinned"] = (tweet_id == pinned_tweet_id)
                        break

        # Engagement metrics
        # Reply count
        reply_el = tweet_el.select_one(SELECTORS["reply_button"])
        if reply_el:
            tweet["reply_count_raw"] = _extract_metric(reply_el)

        # Retweet/repost count
        retweet_el = tweet_el.select_one(SELECTORS["retweet_button"])
        if retweet_el:
            tweet["repost_count_raw"] = _extract_metric(retweet_el)

        # Like count
        like_el = tweet_el.select_one(SELECTORS["like_button"])
        if like_el:
            tweet["like_count_raw"] = _extract_metric(like_el)

        # View count
        views_el = tweet_el.select_one(SELECTORS["views"])
        if views_el:
            tweet["view_count_raw"] = views_el.get_text(strip=True)

        # Tweet timestamp - extract from <time datetime="..."> element
        time_el = tweet_el.select_one("time[datetime]")
        if time_el:
            tweet["created_at_raw"] = time_el.get("datetime")

        # Media URLs
        media_urls = []
        img_elements = tweet_el.select('img[src*="pbs.twimg.com/media"]')
        for img in img_elements:
            src = img.get("src")
            if src:
                media_urls.append(src)
        if media_urls:
            tweet["media_urls"] = media_urls

        # Only add tweet if we have an ID
        if tweet.get("tweet_id"):
            tweets.append(tweet)

    return tweets


def _extract_metric(element) -> str:
    """Extract metric count from a button element."""
    # Metrics are usually in aria-label or nested spans
    aria_label = element.get("aria-label", "")
    if aria_label:
        # Format: "123 Replies" or "1.2K Likes"
        parts = aria_label.split()
        if parts:
            return parts[0]

    # Fallback to text content
    span = element.find("span")
    if span:
        return span.get_text(strip=True)

    return "0"


def parse_page(html: str, username: str | None = None) -> ParseResult:
    """
    Full page parsing - extracts profile and tweets.

    Args:
        html: Raw HTML content
        username: Profile username

    Returns:
        ParseResult with profile_data, tweets_data, and any parse_errors
    """
    soup = BeautifulSoup(html, "lxml")
    errors = []

    # Parse profile
    try:
        profile_data = parse_profile(soup)
    except Exception as e:
        profile_data = {}
        errors.append(f"Profile parse error: {e}")

    # Parse tweets
    try:
        tweets_data = parse_tweets(soup, username)
    except Exception as e:
        tweets_data = []
        errors.append(f"Tweets parse error: {e}")

    return ParseResult(
        profile_data=profile_data,
        tweets_data=tweets_data,
        parse_errors=errors,
    )
