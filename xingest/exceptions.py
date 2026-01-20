"""Custom exception hierarchy for xingest."""


class XingestError(Exception):
    """Base exception for all xingest errors."""


class FetchError(XingestError):
    """Failed to fetch page."""


class PageBlockedError(FetchError):
    """Detected bot blocking or rate limit."""


class ProfileNotFoundError(FetchError):
    """Profile does not exist or is suspended."""


class ParseError(XingestError):
    """Failed to parse page content."""


class CacheError(XingestError):
    """Cache operation failed."""


class ConfigError(XingestError):
    """Invalid configuration."""
