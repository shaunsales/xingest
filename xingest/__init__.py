"""xingest - X/Twitter profile scraper."""

from xingest.models.profile import ProfileData
from xingest.models.tweet import TweetData
from xingest.models.result import ScrapeResult
from xingest.config import ScraperConfig
from xingest.core.orchestrator import Scraper
from xingest.core.exporter import to_json, to_dict, save_json, load_json

__version__ = "0.1.0"

__all__ = [
    # Main interface
    "Scraper",
    "ScraperConfig",
    # Models
    "ProfileData",
    "TweetData",
    "ScrapeResult",
    # Export utilities
    "to_json",
    "to_dict",
    "save_json",
    "load_json",
    "__version__",
]
