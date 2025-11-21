"""Liquidity and order book analytics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class OrderBookSnapshot:
    bids: Sequence[tuple[float, float]]
    asks: Sequence[tuple[float, float]]

    def spread(self) -> float:
        if not self.bids or not self.asks:
            return float("nan")
        return self.asks[0][0] - self.bids[0][0]

    def depth(self, side: str, level: int = 5) -> float:
        levels = self.bids if side.lower() == "bid" else self.asks
        depth = 0.0
        for entry in levels[:level]:
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                try:
                    depth += float(entry[1])
                except (TypeError, ValueError):  # ignore malformed volume entries
                    continue
        return depth


class LiquidityAnalyzer:
    """Compute liquidity metrics from order book snapshots."""

    def imbalance(self, snapshot: OrderBookSnapshot, level: int = 5) -> float:
        bid_depth = snapshot.depth("bid", level)
        ask_depth = snapshot.depth("ask", level)
        if bid_depth + ask_depth == 0:
            return 0.0
        return (bid_depth - ask_depth) / (bid_depth + ask_depth)

    def mid_price(self, snapshot: OrderBookSnapshot) -> float:
        if not snapshot.bids or not snapshot.asks:
            return float("nan")
        return (snapshot.bids[0][0] + snapshot.asks[0][0]) / 2
