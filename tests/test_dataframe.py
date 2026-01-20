"""Unit tests for DataFrame export utilities - uses JSON fixtures, no internet."""

import pytest
from pathlib import Path

from xingest.core.exporter import (
    to_tweets_df,
    to_profile_df,
    results_to_tweets_df,
    results_to_profiles_df,
    save_csv,
    load_json,
)

# Skip all tests if pandas not installed
pd = pytest.importorskip("pandas")

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(username: str):
    """Load ScrapeResult from JSON fixture."""
    return load_json(FIXTURES_DIR / f"{username}.json")


class TestToTweetsDf:
    """Test single result tweet DataFrame conversion."""

    def test_returns_dataframe(self):
        result = load_fixture("okx")
        df = to_tweets_df(result)
        assert isinstance(df, pd.DataFrame)

    def test_has_correct_row_count(self):
        result = load_fixture("okx")
        df = to_tweets_df(result)
        assert len(df) == len(result.tweets)

    def test_has_tweet_columns(self):
        result = load_fixture("okx")
        df = to_tweets_df(result)
        assert "tweet_id" in df.columns
        assert "text" in df.columns
        assert "like_count" in df.columns
        assert "created_at" in df.columns

    def test_includes_username_column(self):
        result = load_fixture("okx")
        df = to_tweets_df(result)
        assert "username" in df.columns
        assert all(df["username"] == "okx")

    def test_preserves_tweet_ids(self):
        result = load_fixture("okx")
        df = to_tweets_df(result)
        expected_ids = {t.tweet_id for t in result.tweets}
        actual_ids = set(df["tweet_id"])
        assert expected_ids == actual_ids


class TestToProfileDf:
    """Test single result profile DataFrame conversion."""

    def test_returns_dataframe(self):
        result = load_fixture("okx")
        df = to_profile_df(result)
        assert isinstance(df, pd.DataFrame)

    def test_has_one_row(self):
        result = load_fixture("okx")
        df = to_profile_df(result)
        assert len(df) == 1

    def test_has_profile_columns(self):
        result = load_fixture("okx")
        df = to_profile_df(result)
        assert "username" in df.columns
        assert "display_name" in df.columns
        assert "followers_count" in df.columns
        assert "following_count" in df.columns

    def test_preserves_username(self):
        result = load_fixture("okx")
        df = to_profile_df(result)
        assert df.iloc[0]["username"] == "okx"


class TestResultsToTweetsDf:
    """Test multiple results tweet DataFrame conversion."""

    def test_combines_multiple_results(self):
        results = [load_fixture("okx"), load_fixture("okx")]
        df = results_to_tweets_df(results)
        
        # Should have tweets from both results
        single_count = len(load_fixture("okx").tweets)
        assert len(df) == single_count * 2

    def test_includes_username_column(self):
        results = [load_fixture("okx")]
        df = results_to_tweets_df(results)
        assert "username" in df.columns

    def test_empty_results(self):
        df = results_to_tweets_df([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestResultsToProfilesDf:
    """Test multiple results profile DataFrame conversion."""

    def test_combines_multiple_results(self):
        results = [load_fixture("okx"), load_fixture("okx")]
        df = results_to_profiles_df(results)
        assert len(df) == 2

    def test_empty_results(self):
        df = results_to_profiles_df([])
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestSaveCsv:
    """Test CSV export functionality."""

    def test_save_tweets_csv(self, tmp_path):
        result = load_fixture("okx")
        filepath = tmp_path / "tweets.csv"
        
        returned_path = save_csv(result, filepath, tweets=True)
        
        assert returned_path == filepath
        assert filepath.exists()
        
        # Verify content
        df = pd.read_csv(filepath)
        assert len(df) == len(result.tweets)

    def test_save_profile_csv(self, tmp_path):
        result = load_fixture("okx")
        filepath = tmp_path / "profile.csv"
        
        save_csv(result, filepath, tweets=False)
        
        assert filepath.exists()
        df = pd.read_csv(filepath)
        assert len(df) == 1
        assert df.iloc[0]["username"] == "okx"

    def test_creates_parent_dirs(self, tmp_path):
        result = load_fixture("okx")
        filepath = tmp_path / "nested" / "dir" / "tweets.csv"
        
        save_csv(result, filepath)
        
        assert filepath.exists()
