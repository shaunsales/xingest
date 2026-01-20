"""Unit tests for HTML parsing - uses cached fixtures, no internet required."""

import pytest
from pathlib import Path

from xingest.core.parser import parse_page
from xingest.core.transformer import transform_result


FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Expected data for validation
EXPECTED_DATA = {
    "okx": {
        "pinned_tweet_id": "2012952460877607151",
        "min_tweets": 3,
    },
    "nodepay": {
        "pinned_tweet_id": "1995827194640138476",
        "min_tweets": 3,
    },
    "jason": {
        "pinned_tweet_id": "2013402546614702147",
        "min_tweets": 3,
    },
    "cz_binance": {
        "pinned_tweet_id": "1981404850832494666",
        "min_tweets": 3,
    },
    "nikitabier": {
        "pinned_tweet_id": None,  # No pinned tweet
        "min_tweets": 3,
    },
}


def get_fixture_html(username: str) -> str:
    """Load HTML fixture for a username."""
    fixture_path = FIXTURES_DIR / f"{username}.html"
    if not fixture_path.exists():
        pytest.skip(f"Fixture not found: {fixture_path}")
    return fixture_path.read_text(encoding="utf-8")


class TestParserWithFixtures:
    """Test parser against cached HTML fixtures."""

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_parse_extracts_profile(self, username: str):
        """Profile data should be extracted from fixture."""
        html = get_fixture_html(username)
        result = parse_page(html, username)
        
        assert result.profile_data, f"No profile data extracted for @{username}"
        assert result.profile_data.get("username") == username
        assert result.profile_data.get("display_name"), "Missing display_name"
        assert result.profile_data.get("followers_count_raw"), "Missing followers_count"

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_parse_extracts_tweets(self, username: str):
        """Tweets should be extracted from fixture."""
        html = get_fixture_html(username)
        result = parse_page(html, username)
        expected = EXPECTED_DATA[username]
        
        assert len(result.tweets_data) >= expected["min_tweets"], \
            f"Expected at least {expected['min_tweets']} tweets for @{username}"

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_all_tweets_have_timestamp(self, username: str):
        """Every tweet must have a created_at timestamp."""
        html = get_fixture_html(username)
        result = parse_page(html, username)
        
        for tweet in result.tweets_data:
            assert tweet.get("created_at_raw"), \
                f"Tweet {tweet.get('tweet_id')} missing created_at_raw"

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_all_tweets_have_id(self, username: str):
        """Every tweet must have a tweet_id."""
        html = get_fixture_html(username)
        result = parse_page(html, username)
        
        for i, tweet in enumerate(result.tweets_data):
            assert tweet.get("tweet_id"), f"Tweet {i} missing tweet_id"

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_pinned_tweet_detection(self, username: str):
        """Pinned tweet should be correctly identified."""
        html = get_fixture_html(username)
        result = parse_page(html, username)
        expected = EXPECTED_DATA[username]
        
        pinned_tweets = [t for t in result.tweets_data if t.get("is_pinned")]
        
        if expected["pinned_tweet_id"]:
            assert len(pinned_tweets) == 1, \
                f"Expected 1 pinned tweet for @{username}, got {len(pinned_tweets)}"
            assert pinned_tweets[0]["tweet_id"] == expected["pinned_tweet_id"], \
                f"Wrong pinned tweet ID for @{username}"
        else:
            assert len(pinned_tweets) == 0, \
                f"Expected no pinned tweets for @{username}, got {len(pinned_tweets)}"


class TestTransformerWithFixtures:
    """Test transformer against cached HTML fixtures."""

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_transform_produces_valid_result(self, username: str):
        """Transform should produce a valid ScrapeResult."""
        html = get_fixture_html(username)
        parse_result = parse_page(html, username)
        
        scrape_result = transform_result(parse_result, username)
        
        assert scrape_result.success, f"Transform failed for @{username}"
        assert scrape_result.profile is not None
        assert len(scrape_result.tweets) > 0

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_transform_normalizes_counts(self, username: str):
        """Counts should be normalized to integers."""
        html = get_fixture_html(username)
        parse_result = parse_page(html, username)
        scrape_result = transform_result(parse_result, username)
        
        assert isinstance(scrape_result.profile.followers_count, int)
        assert scrape_result.profile.followers_count > 0
        
        for tweet in scrape_result.tweets:
            assert isinstance(tweet.like_count, int)

    @pytest.mark.parametrize("username", EXPECTED_DATA.keys())
    def test_transform_parses_timestamps(self, username: str):
        """Timestamps should be parsed to datetime objects."""
        html = get_fixture_html(username)
        parse_result = parse_page(html, username)
        scrape_result = transform_result(parse_result, username)
        
        for tweet in scrape_result.tweets:
            assert tweet.created_at is not None, \
                f"Tweet {tweet.tweet_id} has null created_at after transform"
