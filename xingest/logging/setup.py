"""Structlog configuration for xingest."""

import logging
import sys

import structlog

from xingest.config import ScraperConfig, LogFormat


def configure_logging(config: ScraperConfig | None = None) -> None:
    """
    Configure structlog with appropriate processors and output format.

    Args:
        config: ScraperConfig instance, uses defaults if None
    """
    if config is None:
        config = ScraperConfig()

    # Set up standard library logging
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Common processors
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Add format-specific processors
    if config.log_format == LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend([
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(colors=True),
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.

    Args:
        name: Optional logger name for context

    Returns:
        Configured structlog BoundLogger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger_name=name)
    return logger
