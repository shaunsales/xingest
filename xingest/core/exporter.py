"""Export utilities for scrape results."""

import json
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

from xingest.models.result import ScrapeResult

if TYPE_CHECKING:
    import pandas as pd

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def to_json(result: ScrapeResult, indent: int = 2) -> str:
    """
    Convert ScrapeResult to JSON string.

    Args:
        result: ScrapeResult to serialize
        indent: JSON indentation level

    Returns:
        JSON string
    """
    return result.model_dump_json(indent=indent)


def to_dict(result: ScrapeResult) -> dict:
    """
    Convert ScrapeResult to dictionary.

    Args:
        result: ScrapeResult to convert

    Returns:
        Dictionary representation
    """
    return result.model_dump(mode="json")


def save_json(
    result: ScrapeResult,
    filepath: str | Path,
    indent: int = 2,
) -> Path:
    """
    Save ScrapeResult to JSON file.

    Args:
        result: ScrapeResult to save
        filepath: Output file path
        indent: JSON indentation level

    Returns:
        Path to saved file
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.model_dump_json(indent=indent), encoding="utf-8")
    return path


def save_many_json(
    results: list[ScrapeResult],
    output_dir: str | Path,
    filename_template: str = "{username}.json",
) -> list[Path]:
    """
    Save multiple ScrapeResults to individual JSON files.

    Args:
        results: List of ScrapeResults
        output_dir: Directory for output files
        filename_template: Template with {username} placeholder

    Returns:
        List of paths to saved files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    saved = []
    for result in results:
        if result.profile:
            filename = filename_template.format(username=result.profile.username)
            filepath = output_path / filename
            save_json(result, filepath)
            saved.append(filepath)
    
    return saved


def load_json(filepath: str | Path) -> ScrapeResult:
    """
    Load ScrapeResult from JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        ScrapeResult instance
    """
    path = Path(filepath)
    return ScrapeResult.model_validate_json(path.read_text(encoding="utf-8"))


def merge_results(results: list[ScrapeResult]) -> dict:
    """
    Merge multiple ScrapeResults into a single export-friendly dict.

    Args:
        results: List of ScrapeResults

    Returns:
        Dict with 'profiles' and 'tweets' arrays, plus metadata
    """
    profiles = []
    tweets = []
    
    for result in results:
        if result.profile:
            profiles.append(result.profile.model_dump(mode="json"))
        for tweet in result.tweets:
            tweet_data = tweet.model_dump(mode="json")
            if result.profile:
                tweet_data["_username"] = result.profile.username
            tweets.append(tweet_data)
    
    return {
        "exported_at": datetime.now().isoformat(),
        "profiles_count": len(profiles),
        "tweets_count": len(tweets),
        "profiles": profiles,
        "tweets": tweets,
    }


def _check_pandas():
    """Raise ImportError if pandas is not available."""
    if not PANDAS_AVAILABLE:
        raise ImportError(
            "pandas is required for DataFrame export. Install with: pip install pandas"
        )


def to_tweets_df(result: ScrapeResult) -> "pd.DataFrame":
    """
    Convert tweets from a ScrapeResult to a pandas DataFrame.

    Args:
        result: ScrapeResult containing tweets

    Returns:
        DataFrame with one row per tweet

    Raises:
        ImportError: If pandas is not installed
    """
    _check_pandas()

    rows = []
    for tweet in result.tweets:
        row = tweet.model_dump(mode="json")
        if result.profile:
            row["username"] = result.profile.username
        rows.append(row)

    return pd.DataFrame(rows)


def to_profile_df(result: ScrapeResult) -> "pd.DataFrame":
    """
    Convert profile from a ScrapeResult to a pandas DataFrame.

    Args:
        result: ScrapeResult containing profile

    Returns:
        DataFrame with one row for the profile

    Raises:
        ImportError: If pandas is not installed
    """
    _check_pandas()

    if result.profile:
        row = result.profile.model_dump(mode="json")
        return pd.DataFrame([row])
    return pd.DataFrame()


def results_to_tweets_df(results: list[ScrapeResult]) -> "pd.DataFrame":
    """
    Convert tweets from multiple ScrapeResults to a single DataFrame.

    Args:
        results: List of ScrapeResults

    Returns:
        DataFrame with all tweets, includes 'username' column

    Raises:
        ImportError: If pandas is not installed
    """
    _check_pandas()

    rows = []
    for result in results:
        for tweet in result.tweets:
            row = tweet.model_dump(mode="json")
            if result.profile:
                row["username"] = result.profile.username
            rows.append(row)

    return pd.DataFrame(rows)


def results_to_profiles_df(results: list[ScrapeResult]) -> "pd.DataFrame":
    """
    Convert profiles from multiple ScrapeResults to a single DataFrame.

    Args:
        results: List of ScrapeResults

    Returns:
        DataFrame with one row per profile

    Raises:
        ImportError: If pandas is not installed
    """
    _check_pandas()

    rows = []
    for result in results:
        if result.profile:
            rows.append(result.profile.model_dump(mode="json"))

    return pd.DataFrame(rows)


def save_csv(
    result: ScrapeResult,
    filepath: str | Path,
    tweets: bool = True,
) -> Path:
    """
    Save ScrapeResult to CSV file.

    Args:
        result: ScrapeResult to save
        filepath: Output file path
        tweets: If True, save tweets; if False, save profile

    Returns:
        Path to saved file

    Raises:
        ImportError: If pandas is not installed
    """
    _check_pandas()

    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    if tweets:
        df = to_tweets_df(result)
    else:
        df = to_profile_df(result)

    df.to_csv(path, index=False)
    return path
