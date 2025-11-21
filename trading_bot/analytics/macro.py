"""Macro and microeconomic data ingestion interfaces."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

import requests

from trading_bot.connectors.okx import OkxConnector

logger = logging.getLogger(__name__)


@dataclass
class MacroEvent:
    timestamp: datetime
    source: str
    description: str
    importance: str
    impact: Optional[str] = None


class MacroDataProvider:
    """Base interface for macroeconomic event feeds."""

    def latest_events(self, limit: int = 10) -> Iterable[MacroEvent]:
        raise NotImplementedError


@dataclass
class OnChainMetric:
    name: str
    value: float
    timestamp: datetime


class OnChainDataProvider:
    """Base interface for on-chain micro data."""

    def latest_metrics(self, asset: str, limit: int = 10) -> Iterable[OnChainMetric]:
        raise NotImplementedError


class NullMacroProvider(MacroDataProvider):
    """Fallback provider that returns no macro events."""

    def latest_events(self, limit: int = 10) -> Iterable[MacroEvent]:  # noqa: D401
        return []


class NullOnChainProvider(OnChainDataProvider):
    """Fallback provider that returns no on-chain metrics."""

    def latest_metrics(self, asset: str, limit: int = 10) -> Iterable[OnChainMetric]:  # noqa: D401
        return []


class OkxMarketMacroProvider(MacroDataProvider):
    """Derive macro-style insights from OKX market data."""

    def __init__(self, okx: OkxConnector, symbols: Iterable[str]) -> None:
        self._okx = okx
        self._symbols = list(symbols)

    def set_symbols(self, symbols: Iterable[str]) -> None:
        self._symbols = list(symbols)

    def latest_events(self, limit: int = 10) -> Iterable[MacroEvent]:  # noqa: D401
        events: list[MacroEvent] = []
        for symbol in self._symbols:
            if len(events) >= limit:
                break
            try:
                ticker = self._okx.fetch_ticker(symbol)
            except Exception as exc:  # noqa: BLE001
                logger.warning("OKX macro fetch failed for %s: %s", symbol, exc)
                continue

            change_pct = float(ticker.get("percentage") or 0.0)
            volume_quote = ticker.get("quoteVolume")
            if volume_quote is None:
                volume_quote = ticker.get("info", {}).get("volCcy24h") or 0.0
            try:
                volume_quote = float(volume_quote)
            except (TypeError, ValueError):
                volume_quote = 0.0

            high = ticker.get("high") or ticker.get("highPrice")
            low = ticker.get("low") or ticker.get("lowPrice")

            importance = "high" if abs(change_pct) >= 5 else "medium" if abs(change_pct) >= 2 else "low"
            impact = "positive" if change_pct > 0 else "negative" if change_pct < 0 else "neutral"
            description = (
                f"{symbol.lower()} change={change_pct:.2f}% volume={volume_quote:.2f} "
                f"high={high} low={low}"
            )

            events.append(
                MacroEvent(
                    timestamp=datetime.utcnow(),
                    source="OKX",
                    description=description,
                    importance=importance,
                    impact=impact,
                )
            )

        return events


class OkxMarketOnChainProvider(OnChainDataProvider):
    """Proxy on-chain style metrics using OKX depth and volume data."""

    def __init__(self, okx: OkxConnector) -> None:
        self._okx = okx

    def latest_metrics(self, asset: str, limit: int = 10) -> Iterable[OnChainMetric]:  # noqa: D401
        symbol = self._normalize_symbol(asset)

        try:
            ticker = self._okx.fetch_ticker(symbol)
            order_book = self._okx.fetch_order_book(symbol, limit=5)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OKX micro fetch failed for %s (normalized %s): %s", asset, symbol, exc)
            return []

        now = datetime.utcnow()
        metrics: list[OnChainMetric] = []

        base_volume = ticker.get("baseVolume") or ticker.get("info", {}).get("vol24h")
        quote_volume = ticker.get("quoteVolume") or ticker.get("info", {}).get("volCcy24h")
        high = ticker.get("high") or ticker.get("highPrice")
        low = ticker.get("low") or ticker.get("lowPrice")

        try:
            metrics.append(OnChainMetric(name="base_volume_24h", value=float(base_volume or 0.0), timestamp=now))
        except (TypeError, ValueError):
            pass

        try:
            metrics.append(OnChainMetric(name="quote_volume_24h", value=float(quote_volume or 0.0), timestamp=now))
        except (TypeError, ValueError):
            pass

        if high is not None and low is not None:
            try:
                range_pct = (float(high) - float(low)) / float(low) * 100 if float(low) else 0.0
                metrics.append(OnChainMetric(name="daily_range_pct", value=float(range_pct), timestamp=now))
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        bids = order_book.get("bids", [])[:5]
        asks = order_book.get("asks", [])[:5]
        try:
            bid_depth = sum(float(level[1]) for level in bids if len(level) >= 2)
            ask_depth = sum(float(level[1]) for level in asks if len(level) >= 2)
            metrics.append(OnChainMetric(name="bid_depth_top5", value=bid_depth, timestamp=now))
            metrics.append(OnChainMetric(name="ask_depth_top5", value=ask_depth, timestamp=now))
        except (TypeError, ValueError):
            pass

        return metrics[:limit]

    @staticmethod
    def _normalize_symbol(asset: str) -> str:
        if not asset:
            return "BTC/USDT"

        token = asset.strip().upper()
        if "/" in token:
            base, quote = token.split("/", 1)
            base = base.split(":")[-1]
            return f"{base}/{quote}"

        base = token.split(":")[-1]
        return f"{base}/USDT"


class CryptoPanicMacroProvider(MacroDataProvider):
    """Fetch macro-style crypto sentiment events from the CryptoPanic API."""

    API_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, api_key: str, *, currency: str = "BTC") -> None:
        self._api_key = api_key
        self._currency = currency

    def latest_events(self, limit: int = 10) -> Iterable[MacroEvent]:  # noqa: D401
        params = {
            "auth_token": self._api_key,
            "currencies": self._currency,
            "public": "true",
        }
        try:
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            payload = response.json().get("results", [])
        except requests.RequestException as exc:  # noqa: BLE001
            logger.warning("CryptoPanic fetch failed: %s", exc)
            return []

        events: list[MacroEvent] = []
        for item in payload[:limit]:
            published_at = item.get("published_at")
            if not published_at:
                continue
            timestamp = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            importance = "high" if item.get("importance") == "high" else "medium"
            events.append(
                MacroEvent(
                    timestamp=timestamp,
                    source="CryptoPanic",
                    description=item.get("title", ""),
                    importance=importance,
                    impact=item.get("kind"),
                )
            )

        return events


class DefiLlamaOnChainProvider(OnChainDataProvider):
    """Retrieve on-chain metrics using the public DeFiLlama price API."""

    API_URL = "https://coins.llama.fi/prices/current/"

    SYMBOL_MAPPING = {
        "BTC/USDT": "coingecko:bitcoin",
        "ETH/USDT": "coingecko:ethereum",
    }

    def map_symbol(self, asset: str) -> str:
        return self.SYMBOL_MAPPING.get(asset.upper(), asset)

    def latest_metrics(self, asset: str, limit: int = 10) -> Iterable[OnChainMetric]:  # noqa: D401
        mapped_asset = self.map_symbol(asset)
        url = f"{self.API_URL}{mapped_asset}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json().get("coins", {})
        except requests.RequestException as exc:  # noqa: BLE001
            logger.warning("DeFiLlama fetch failed for %s: %s", asset, exc)
            return []

        coin = data.get(mapped_asset)
        if not coin:
            logger.info("No on-chain data returned for %s", asset)
            return []

        timestamp = datetime.fromtimestamp(coin.get("timestamp", 0))
        metrics = [
            OnChainMetric(name="price", value=float(coin.get("price", 0.0)), timestamp=timestamp),
        ]

        market_cap = coin.get("marketCap")
        if market_cap is not None:
            metrics.append(OnChainMetric(name="market_cap", value=float(market_cap), timestamp=timestamp))

        return metrics[:limit]
