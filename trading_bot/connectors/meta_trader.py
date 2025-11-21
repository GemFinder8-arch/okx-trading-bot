"""MetaTrader 5 connector abstraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional

import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


@dataclass
class MetaTraderCredentials:
    """Login credentials required for authenticated MetaTrader sessions."""

    login: Optional[int] = None
    password: Optional[str] = None
    server: Optional[str] = None


class MetaTraderConnector:
    """High-level wrapper around MetaTrader5 native functions."""

    def __init__(
        self,
        credentials: Optional[MetaTraderCredentials] = None,
        *,
        auto_initialize: bool = True,
    ) -> None:
        self._credentials = credentials or MetaTraderCredentials()
        if auto_initialize:
            self.initialize()

    # ------------------------------------------------------------------
    # Lifecycle management
    # ------------------------------------------------------------------
    def initialize(self) -> bool:
        """Ensure MT5 is initialized with the provided credentials."""

        if mt5.initialize():
            if self._credentials.login:
                authorized = mt5.login(
                    self._credentials.login,
                    password=self._credentials.password,
                    server=self._credentials.server,
                )
                if not authorized:
                    logger.error("MT5 login failed: %s", mt5.last_error())
                    return False
            logger.info("MetaTrader5 initialized successfully")
            return True

        error = mt5.last_error()
        logger.error("Failed to initialize MetaTrader5: %s", error)
        return False

    def shutdown(self) -> None:
        """Gracefully shutdown MetaTrader client session."""

        if mt5.shutdown():
            logger.info("MetaTrader5 shutdown completed")
        else:
            logger.warning("MetaTrader5 shutdown reported failure")

    # ------------------------------------------------------------------
    # Market data helpers
    # ------------------------------------------------------------------
    def ensure_initialized(self) -> None:
        """Raise if MetaTrader API is not initialized."""

        if not mt5.initialize():  # mt5.initialize returns True if already connected
            raise RuntimeError("MetaTrader5 is not initialized")

    def get_symbol_info(self, symbol: str) -> Optional[mt5.SymbolInfo]:
        self.ensure_initialized()
        return mt5.symbol_info(symbol)

    def get_tick(self, symbol: str) -> Optional[mt5.Tick]:
        self.ensure_initialized()
        return mt5.symbol_info_tick(symbol)

    def get_mid_price(self, symbol: str) -> Optional[float]:
        tick = self.get_tick(symbol)
        if not tick:
            return None
        return (tick.ask + tick.bid) / 2

    # ------------------------------------------------------------------
    # Trading helpers
    # ------------------------------------------------------------------
    def positions(self, symbol: Optional[str] = None) -> Optional[Iterable[mt5.TradePosition]]:
        self.ensure_initialized()
        return mt5.positions_get(symbol=symbol)

    def orders(self, symbol: Optional[str] = None) -> Optional[Iterable[mt5.TradeOrder]]:
        self.ensure_initialized()
        return mt5.orders_get(symbol=symbol)

    def send_order(self, request: Dict[str, Any]) -> mt5.TradeResult:
        self.ensure_initialized()
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Order send failed: retcode=%s info=%s", result.retcode, result)
        return result

    def close_position(self, position: mt5.TradePosition, *, deviation: int = 20) -> mt5.TradeResult:
        """Close an open position by executing the opposite trade."""

        tick = self.get_tick(position.symbol)
        if tick is None:
            raise RuntimeError(f"Unable to fetch tick for symbol {position.symbol}")

        price = tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask
        order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": deviation,
            "magic": 0,
            "comment": "Cascade bot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        return self.send_order(request)

    def modify_order(self, request: Dict[str, Any]) -> mt5.TradeResult:
        self.ensure_initialized()
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error("Order modification failed: %s", result)
        return result
