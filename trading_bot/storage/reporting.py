"""Storage helpers for token ranking reports."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from trading_bot.analytics.token_ranking import TokenScore


def save_token_report(scores: Iterable[TokenScore], path: Path) -> None:
    """Persist ranked token scores to disk as JSON."""

    payload = [asdict(score) | {"total": score.total} for score in scores]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
