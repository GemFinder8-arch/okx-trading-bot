"""Technical indicator computation utilities."""

from __future__ import annotations

from typing import Iterable, List

import numpy as np


def ema(values: Iterable[float], window: int) -> List[float]:
    """Compute the Exponential Moving Average for a sequence of prices."""

    values_array = np.asarray(list(values), dtype=float)
    if values_array.size < window:
        raise ValueError("Window larger than input series")

    weights = np.exp(np.linspace(-1.0, 0.0, window))
    weights /= weights.sum()

    ema_values = np.convolve(values_array, weights, mode="full")[: values_array.size]
    ema_values[: window] = ema_values[window]
    return ema_values.tolist()


def rsi(values: Iterable[float], window: int = 14) -> List[float]:
    """Compute Relative Strength Index over the provided price series."""

    values_array = np.asarray(list(values), dtype=float)
    if values_array.size <= window:
        raise ValueError("Input data length must exceed RSI window")

    deltas = np.diff(values_array)
    seed = deltas[:window]
    up = seed[seed > 0].sum() / window
    down = -seed[seed < 0].sum() / window
    rs = up / down if down != 0 else np.inf
    rsi_series = np.zeros_like(values_array)
    rsi_series[: window] = 100.0 - (100.0 / (1.0 + rs))

    up_vals = np.zeros_like(deltas)
    down_vals = np.zeros_like(deltas)
    up_vals[deltas > 0] = deltas[deltas > 0]
    down_vals[deltas < 0] = -deltas[deltas < 0]

    up_avg = up
    down_avg = down
    for i in range(window, len(values_array)):
        up_avg = (up_avg * (window - 1) + up_vals[i - 1]) / window
        down_avg = (down_avg * (window - 1) + down_vals[i - 1]) / window
        rs = up_avg / down_avg if down_avg != 0 else np.inf
        rsi_series[i] = 100.0 - (100.0 / (1.0 + rs))

    return rsi_series.tolist()
