"""Configuration module with enhanced validation."""

# Import original config functions to maintain compatibility
from trading_bot.config.config import (
    build_macro_provider,
    build_okx_connector,
    build_onchain_provider,
    load_from_env,
    Config,
)

# Import enhanced configuration
from trading_bot.config.enhanced_config import (
    EnhancedBotConfig,
    load_enhanced_config,
)

__all__ = [
    "build_macro_provider", 
    "build_okx_connector",
    "build_onchain_provider",
    "load_from_env",
    "Config",
    "EnhancedBotConfig",
    "load_enhanced_config",
]
