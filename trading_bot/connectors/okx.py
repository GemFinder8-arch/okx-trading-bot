"""OKX exchange connector with enhanced error handling and circuit breaker protection."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import ccxt
from trading_bot.infrastructure.circuit_breaker import CircuitBreakerConfig, get_circuit_breaker

logger = logging.getLogger(__name__)


@dataclass
class OkxCredentials:
    api_key: str
    api_secret: str
    passphrase: str


class OkxConnector:
    """Thin wrapper around ccxt.okx for spot trading."""

    def __init__(
        self,
        credentials: Optional[OkxCredentials] = None,
        *,
        enable_rate_limit: bool = True,
        sandbox: bool = False,
    ) -> None:
        params: Dict[str, Any] = {
            "enableRateLimit": enable_rate_limit,
            "options": {"defaultType": "spot"},
        }

        self._client = ccxt.okx(params)
        self._client.set_sandbox_mode(sandbox)

        if credentials:
            self._client.apiKey = credentials.api_key
            self._client.secret = credentials.api_secret
            self._client.password = credentials.passphrase
        else:
            logger.warning("OkxConnector initialized without credentials; public endpoints only")
        
        # Initialize circuit breakers
        # Circuit breaker configuration - more conservative for rate limiting
        self.market_data_breaker = get_circuit_breaker(
            "okx_market_data",
            CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30.0)
        )
        self.trading_breaker = get_circuit_breaker(
            "okx_trading",
            CircuitBreakerConfig(failure_threshold=20, recovery_timeout=10.0)  # Much more tolerant
        )
        
        # Set fallback functions
        self.market_data_breaker.set_fallback(self._market_data_fallback)
        self.trading_breaker.set_fallback(self._trading_fallback)

    # ------------------------------------------------------------------
    # Market data
    # ------------------------------------------------------------------
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        return self.market_data_breaker.call(self._client.fetch_ticker, symbol)

    def fetch_order_book(self, symbol: str, limit: int = 50) -> Dict[str, Any]:
        return self.market_data_breaker.call(self._client.fetch_order_book, symbol, limit=limit)

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 500,
    ) -> list[list[Any]]:
        return self.market_data_breaker.call(self._client.fetch_ohlcv, symbol, timeframe=timeframe, limit=limit)

    def fetch_liquid_spot_symbols(
        self,
        min_quote_volume: float,
        quote_currency: str = "USDT",
        limit: Optional[int] = None,
    ) -> List[Tuple[str, float]]:
        """Return spot symbols meeting the minimum 24h quote volume threshold."""

        try:
            markets = self._client.load_markets()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load OKX markets: %s", exc)
            markets = {}

        try:
            tickers = self._client.fetch_tickers()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch OKX tickers: %s", exc)
            return []

        liquid: List[Tuple[str, float]] = []
        for symbol, ticker in tickers.items():
            market = markets.get(symbol) if markets else None
            if market and not market.get("spot", False):
                continue
            if not symbol.endswith(f"/{quote_currency}"):
                continue

            volume = ticker.get("quoteVolume")
            if volume is None:
                info = ticker.get("info", {})
                volume = info.get("volCcy24h") or info.get("volCcy24H")

            try:
                volume_value = float(volume)
            except (TypeError, ValueError):
                continue

            if volume_value >= min_quote_volume:
                liquid.append((symbol, volume_value))

        liquid.sort(key=lambda item: item[1], reverse=True)
        if limit is not None:
            liquid = liquid[:limit]
        return liquid

    # ------------------------------------------------------------------
    # Market helpers for limits/precision
    # ------------------------------------------------------------------
    def load_markets(self) -> Dict[str, Any]:
        return self._client.load_markets()

    def get_market(self, symbol: str) -> Dict[str, Any]:
        # ensure markets are loaded
        if not getattr(self._client, "markets", None):
            self._client.load_markets()
        return self._client.market(symbol)

    def amount_to_precision(self, symbol: str, amount: float, *, as_string: bool = False):
        precise = self._client.amount_to_precision(symbol, amount)
        return precise if as_string else float(precise)

    def price_to_precision(self, symbol: str, price: float, *, as_string: bool = False):
        precise = self._client.price_to_precision(symbol, price)
        return precise if as_string else float(precise)

    def min_order_amount(self, symbol: str, price: Optional[float]) -> float:
        """Compute the minimal tradable amount considering amount and cost limits."""
        try:
            market = self.get_market(symbol)
        except Exception:
            return 0.0

        limits = market.get("limits", {}) or {}
        min_amount = (limits.get("amount", {}) or {}).get("min") or 0.0
        min_cost = (limits.get("cost", {}) or {}).get("min") or 0.0

        if min_cost and price:
            try:
                amt_from_cost = float(min_cost) / float(price)
                min_amount = max(float(min_amount or 0.0), amt_from_cost)
            except Exception:
                pass

        if min_amount:
            try:
                min_amount = self.amount_to_precision(symbol, float(min_amount))
            except Exception:
                pass
        return float(min_amount or 0.0)

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._client.create_order(symbol, order_type, side, amount, price, params or {})

    def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        return self._client.cancel_order(order_id, symbol)

    def create_algo_order(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an algorithmic (conditional/OCO) order via private REST."""

        return self._client.private_post_trade_order_algo(params)

    def cancel_algo_orders(self, algo_ids: list[str]) -> Dict[str, Any]:
        """Cancel previously placed algo orders by their identifiers."""

        payload = {"algoIds": algo_ids}
        return self._client.private_post_trade_cancel_algs(payload)

    def fetch_balance(self) -> Dict[str, Any]:
        return self.trading_breaker.call(self._client.fetch_balance)
    
    def fetch_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """Fetch order status by ID."""
        return self.trading_breaker.call(self._client.fetch_order, order_id, symbol)
    
    def fetch_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """Fetch all open orders."""
        return self.trading_breaker.call(self._client.fetch_open_orders, symbol)
    
    def fetch_algo_orders(self, order_type: str = "oco") -> Dict[str, Any]:
        """Fetch open algo orders (TP/SL, OCO, conditional orders) from OKX.
        
        Args:
            order_type: Type of algo orders to fetch ("oco", "conditional", "trigger", etc.)
        
        Returns:
            Dict with algo orders data from OKX API
        """
        try:
            # Use OKX private API to fetch algo orders
            # ordType can be: oco, conditional, trigger, etc.
            params = {
                "ordType": order_type,
                "state": "live"  # Only get active orders
            }
            return self._client.private_get_trade_orders_algo_pending(params)
        except Exception as exc:
            logger.warning("Failed to fetch algo orders of type %s: %s", order_type, exc)
            return {"data": []}
    
    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers to allow normal operation."""
        self.market_data_breaker.reset()
        self.trading_breaker.reset()
        logger.info("OKX circuit breakers reset")
    
    # ------------------------------------------------------------------
    # Circuit breaker fallback methods
    # ------------------------------------------------------------------
    def _market_data_fallback(self, *args, **kwargs) -> Dict[str, Any]:
        """Fallback function for market data when circuit breaker is open.
        
        REAL DATA ONLY POLICY: No fake data allowed.
        Raise exception to fail fast instead of returning fake prices.
        """
        symbol = args[0] if args else "unknown"
        logger.error("❌ MARKET DATA CIRCUIT BREAKER OPEN for %s - NO FALLBACK DATA (Real Data Only Policy)", symbol)
        raise Exception(f"Market data unavailable for {symbol} - circuit breaker open. No real data available.")
    
    def _trading_fallback(self, *args, **kwargs) -> Dict[str, Any]:
        """Fallback for trading operations when circuit is open."""
        logger.error("Trading circuit breaker open, cannot execute trades")
        
        # Return error structure
        return {
            "id": None,
            "info": {"error": "Trading circuit breaker open"},
            "timestamp": None,
            "datetime": None,
            "status": "failed",
            "symbol": args[0] if args else None
        }
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "market_data": self.market_data_breaker.get_stats(),
            "trading": self.trading_breaker.get_stats()
        }
