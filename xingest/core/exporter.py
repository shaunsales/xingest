"""Export utilities for scrape results."""

import json
from pathlib import Path
from datetime import datetime

from xingest.models.result import ScrapeResult


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
