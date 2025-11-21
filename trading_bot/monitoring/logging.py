"""Logging configuration utilities."""

from __future__ import annotations

import logging
from typing import Optional


def configure_logging(level: int = logging.INFO, *, log_file: Optional[str] = None) -> None:
    """Configure application-wide logging.

    Parameters
    ----------
    level:
        Default log level for root logger.
    log_file:
        Optional path to a file where logs should be persisted. If omitted,
        logs are emitted to stderr only.
    """

    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
