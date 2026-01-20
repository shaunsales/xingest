"""Unit tests for exporter utilities - uses JSON fixtures, no internet."""

import json
import pytest
from pathlib import Path

from xingest.core.exporter import (
    to_json,
    to_dict,
    save_json,
    load_json,
    merge_results,
)
from xingest.models.result import ScrapeResult


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(username: str) -> ScrapeResult:
    """Load ScrapeResult from JSON fixture."""
    return load_json(FIXTURES_DIR / f"{username}.json")


class TestToJson:
    """Test JSON string conversion."""

    def test_to_json_returns_string(self):
        result = load_fixture("okx")
        json_str = to_json(result)
        assert isinstance(json_str, str)

    def test_to_json_is_valid_json(self):
        result = load_fixture("okx")
        json_str = to_json(result)
        parsed = json.loads(json_str)
        assert "profile" in parsed
        assert "tweets" in parsed

    def test_to_json_preserves_data(self):
        result = load_fixture("okx")
        json_str = to_json(result)
        parsed = json.loads(json_str)
        assert parsed["profile"]["username"] == result.profile.username


class TestToDict:
    """Test dictionary conversion."""

    def test_to_dict_returns_dict(self):
        result = load_fixture("okx")
        d = to_dict(result)
        assert isinstance(d, dict)

    def test_to_dict_has_expected_keys(self):
        result = load_fixture("okx")
        d = to_dict(result)
        assert "profile" in d
        assert "tweets" in d
        assert "success" in d
        assert "scraped_at" in d


class TestSaveLoadJson:
    """Test file I/O operations."""

    def test_save_and_load_roundtrip(self, tmp_path):
        """Save and load should preserve data."""
        original = load_fixture("okx")
        filepath = tmp_path / "test_output.json"
        
        save_json(original, filepath)
        loaded = load_json(filepath)
        
        assert loaded.profile.username == original.profile.username
        assert len(loaded.tweets) == len(original.tweets)

    def test_save_creates_parent_dirs(self, tmp_path):
        """Should create nested directories."""
        original = load_fixture("okx")
        filepath = tmp_path / "nested" / "dir" / "output.json"
        
        save_json(original, filepath)
        
        assert filepath.exists()

    def test_save_returns_path(self, tmp_path):
        """Should return the saved path."""
        original = load_fixture("okx")
        filepath = tmp_path / "test.json"
        
        result_path = save_json(original, filepath)
        
        assert result_path == filepath


class TestMergeResults:
    """Test merging multiple results."""

    def test_merge_single_result(self):
        result = load_fixture("okx")
        merged = merge_results([result])
        
        assert merged["profiles_count"] == 1
        assert merged["tweets_count"] == len(result.tweets)

    def test_merge_multiple_results(self):
        results = [load_fixture("okx")]
        # Add same fixture again to simulate multiple
        results.append(load_fixture("okx"))
        
        merged = merge_results(results)
        
        assert merged["profiles_count"] == 2
        assert len(merged["profiles"]) == 2

    def test_merge_includes_username_in_tweets(self):
        result = load_fixture("okx")
        merged = merge_results([result])
        
        for tweet in merged["tweets"]:
            assert "_username" in tweet
            assert tweet["_username"] == "okx"

    def test_merge_has_metadata(self):
        result = load_fixture("okx")
        merged = merge_results([result])
        
        assert "exported_at" in merged
        assert "profiles_count" in merged
        assert "tweets_count" in merged
