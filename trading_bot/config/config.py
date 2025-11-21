"""Central configuration management for the trading bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class ApiCredentials:
    """Secrets needed for authenticated APIs."""

    api_key: str
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None


@dataclass
class ExchangeConfig:
    """Configuration for a single exchange connector."""

    name: str
    credentials: Optional[ApiCredentials] = None
    sandbox: bool = False
    base_url: Optional[str] = None


@dataclass
class BotSettings:
    """Runtime settings for the trading bot."""

    polling_interval_seconds: int = 60  # Increased to 60s to prevent rate limiting
    max_concurrent_positions: int = 10
    default_symbol_universe: tuple[str, ...] = ("BTC/USDT", "ETH/USDT", "SOL/USDT", "ADA/USDT", "XTZ/USDT")  # Focus on working symbols
    default_trade_volume: float = 0.01
    min_quote_balance: float = 50.0
    min_quote_volume_usd: float = 40_000_000.0
    risk_per_trade_pct: float = 0.05
    max_market_order_notional: float = 1_000.0
    tp_sl_buffer_pct: float = 0.001


@dataclass
class Config:
    """Top-level configuration aggregate."""

    bot: BotSettings
    exchanges: tuple[ExchangeConfig, ...]
    macro_api_key: Optional[str] = None


def load_from_env() -> Config:
    """Load configuration from environment variables.

    Environment variable names:

    - TRADING_BOT_POLLING_INTERVAL
    - TRADING_BOT_MAX_CONCURRENT_POSITIONS
    - TRADING_BOT_SYMBOLS (comma-separated)
    - TRADING_BOT_TRADE_VOLUME
    - TRADING_BOT_MIN_QUOTE_BALANCE
    - TRADING_BOT_MIN_QUOTE_VOLUME_USD
    - TRADING_BOT_RISK_PER_TRADE
    - OKX_API_KEY / OKX_SECRET_KEY / OKX_PASSPHRASE
    - OKX_SANDBOX (optional boolean)
    """

    def _get(name: str, default: Optional[str] = None) -> Optional[str]:
        return os.environ.get(name, default)

    def _get_int(name: str, default: int) -> int:
        value = _get(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _get_float(name: str, default: float) -> float:
        value = _get(name)
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _get_bool(name: str, default: bool = False) -> bool:
        value = _get(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def _get_symbols(name: str, default: Sequence[str]) -> tuple[str, ...]:
        value = _get(name)
        if value is None:
            return tuple(default)
        symbols = [item.strip() for item in value.split(",") if item.strip()]
        return tuple(symbols) if symbols else tuple(default)

    bot_settings = BotSettings(
        polling_interval_seconds=_get_int("TRADING_BOT_POLLING_INTERVAL", 5),
        max_concurrent_positions=_get_int("TRADING_BOT_MAX_CONCURRENT_POSITIONS", 10),
        default_symbol_universe=_get_symbols("TRADING_BOT_SYMBOLS", ("BTC/USDT", "ETH/USDT")),
        default_trade_volume=_get_float("TRADING_BOT_TRADE_VOLUME", 0.01),
        min_quote_balance=_get_float("TRADING_BOT_MIN_QUOTE_BALANCE", 50.0),
        min_quote_volume_usd=_get_float("TRADING_BOT_MIN_QUOTE_VOLUME_USD", 40_000_000.0),
        risk_per_trade_pct=_get_float("TRADING_BOT_RISK_PER_TRADE", 0.05),
        max_market_order_notional=_get_float("TRADING_BOT_MAX_MARKET_NOTIONAL", 1_000.0),
        tp_sl_buffer_pct=_get_float("TRADING_BOT_TP_SL_BUFFER_PCT", 0.001),
    )

    exchanges: list[ExchangeConfig] = []


    okx_key = _get("OKX_API_KEY")
    okx_secret = _get("OKX_SECRET_KEY")
    okx_passphrase = _get("OKX_PASSPHRASE")
    if okx_key and okx_secret and okx_passphrase:
        exchanges.append(
            ExchangeConfig(
                name="okx",
                credentials=ApiCredentials(api_key=okx_key, api_secret=okx_secret, passphrase=okx_passphrase),
                sandbox=_get_bool("OKX_SANDBOX"),
            )
        )

    macro_api_key = _get("TRADING_BOT_MACRO_API_KEY")

    return Config(
        bot=bot_settings,
        exchanges=tuple(exchanges),
        macro_api_key=macro_api_key,
    )






def build_okx_connector(config: Config):
    from trading_bot.connectors.okx import OkxConnector, OkxCredentials

    okx_config = next((ex for ex in config.exchanges if ex.name == "okx"), None)
    credentials = None
    sandbox = False
    if okx_config:
        sandbox = okx_config.sandbox
        if okx_config.credentials:
            cred = okx_config.credentials
            if cred.api_key and cred.api_secret and cred.passphrase:
                credentials = OkxCredentials(
                    api_key=cred.api_key,
                    api_secret=cred.api_secret,
                    passphrase=cred.passphrase,
                )

    return OkxConnector(credentials=credentials, sandbox=sandbox)



def build_macro_provider(config: Config, okx=None):
    from trading_bot.analytics.macro import OkxMarketMacroProvider

    symbols = config.bot.default_symbol_universe
    if okx is None:
        from trading_bot.connectors.okx import OkxConnector, OkxCredentials

        okx_config = next((ex for ex in config.exchanges if ex.name == "okx"), None)
        credentials = None
        sandbox = False
        if okx_config:
            sandbox = okx_config.sandbox
            if okx_config.credentials:
                cred = okx_config.credentials
                if cred.api_key and cred.api_secret and cred.passphrase:
                    credentials = OkxCredentials(
                        api_key=cred.api_key,
                        api_secret=cred.api_secret,
                        passphrase=cred.passphrase,
                    )
        okx = OkxConnector(credentials=credentials, sandbox=sandbox)

    provider = OkxMarketMacroProvider(okx, symbols)
    return provider


def build_onchain_provider(config: Config, okx=None):
    from trading_bot.analytics.macro import OkxMarketOnChainProvider

    if okx is None:
        from trading_bot.connectors.okx import OkxConnector, OkxCredentials

        okx_config = next((ex for ex in config.exchanges if ex.name == "okx"), None)
        credentials = None
        sandbox = False
        if okx_config:
            sandbox = okx_config.sandbox
            if okx_config.credentials:
                cred = okx_config.credentials
                if cred.api_key and cred.api_secret and cred.passphrase:
                    credentials = OkxCredentials(
                        api_key=cred.api_key,
                        api_secret=cred.api_secret,
                        passphrase=cred.passphrase,
                    )
        okx = OkxConnector(credentials=credentials, sandbox=sandbox)
    return OkxMarketOnChainProvider(okx)
