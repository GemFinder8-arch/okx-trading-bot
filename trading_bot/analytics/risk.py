"""Risk analytics utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class RiskMetrics:
    volatility: float
    max_drawdown: float
    sharpe_ratio: float


class RiskAnalyzer:
    """Compute portfolio-level risk indicators from PnL series."""

    def compute(self, pnl_series: Iterable[float], risk_free_rate: float = 0.0) -> RiskMetrics:
        returns = np.asarray(list(pnl_series), dtype=float)
        if returns.size == 0:
            raise ValueError("PnL series cannot be empty")

        volatility = returns.std(ddof=1)
        cumulative = returns.cumsum()
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        max_drawdown = drawdowns.max() if drawdowns.size else 0.0

        avg_return = returns.mean()
        sharpe = (avg_return - risk_free_rate) / volatility if volatility != 0 else 0.0

        return RiskMetrics(volatility=volatility, max_drawdown=max_drawdown, sharpe_ratio=sharpe)
