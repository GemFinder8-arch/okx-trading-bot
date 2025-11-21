"""Enhanced configuration system with validation and bounds checking."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RegimeDetectionConfig:
    """Configuration for market regime detection."""
    lookback_periods: int = 100
    volatility_window: int = 20
    trend_window: int = 50
    trend_threshold: float = 0.3
    volatility_high_percentile: float = 0.8
    volatility_low_percentile: float = 0.2
    ranging_threshold: float = 0.15
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.lookback_periods < 50:
            raise ValueError("lookback_periods must be >= 50")
        if self.volatility_window < 10:
            raise ValueError("volatility_window must be >= 10")
        if self.trend_window < 20:
            raise ValueError("trend_window must be >= 20")
        if not 0.0 <= self.trend_threshold <= 1.0:
            raise ValueError("trend_threshold must be between 0.0 and 1.0")
        if not 0.5 <= self.volatility_high_percentile <= 1.0:
            raise ValueError("volatility_high_percentile must be between 0.5 and 1.0")
        if not 0.0 <= self.volatility_low_percentile <= 0.5:
            raise ValueError("volatility_low_percentile must be between 0.0 and 0.5")


@dataclass
class SentimentAnalysisConfig:
    """Configuration for sentiment analysis."""
    sentiment_window: int = 50
    sentiment_weight: float = 0.2
    fear_threshold: float = 0.7
    greed_threshold: float = 0.7
    uncertainty_threshold: float = 0.6
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.sentiment_window < 20:
            raise ValueError("sentiment_window must be >= 20")
        if not 0.0 <= self.sentiment_weight <= 1.0:
            raise ValueError("sentiment_weight must be between 0.0 and 1.0")
        if not 0.0 <= self.fear_threshold <= 1.0:
            raise ValueError("fear_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.greed_threshold <= 1.0:
            raise ValueError("greed_threshold must be between 0.0 and 1.0")


@dataclass
class DecisionEngineConfig:
    """Configuration for enhanced decision engine."""
    min_confidence_threshold: float = 0.6
    strong_signal_threshold: float = 0.8
    regime_weight: float = 0.4
    sentiment_weight: float = 0.2
    technical_weight: float = 0.4
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.0 <= self.min_confidence_threshold <= 1.0:
            raise ValueError("min_confidence_threshold must be between 0.0 and 1.0")
        if not 0.0 <= self.strong_signal_threshold <= 1.0:
            raise ValueError("strong_signal_threshold must be between 0.0 and 1.0")
        
        # Check weights sum to reasonable total
        total_weight = self.regime_weight + self.sentiment_weight + self.technical_weight
        if not 0.8 <= total_weight <= 1.2:
            logger.warning("Decision weights sum to %.2f (should be close to 1.0)", total_weight)


@dataclass
class RiskManagementConfig:
    """Configuration for enhanced risk management."""
    max_portfolio_risk: float = 0.02
    max_position_risk: float = 0.005
    max_correlation: float = 0.7
    max_drawdown: float = 0.05
    volatility_lookback: int = 30
    kelly_fraction_limit: float = 0.25
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not 0.001 <= self.max_portfolio_risk <= 0.1:
            raise ValueError("max_portfolio_risk must be between 0.1% and 10%")
        if not 0.0001 <= self.max_position_risk <= 0.05:
            raise ValueError("max_position_risk must be between 0.01% and 5%")
        if not 0.0 <= self.max_correlation <= 1.0:
            raise ValueError("max_correlation must be between 0.0 and 1.0")
        if not 0.01 <= self.max_drawdown <= 0.5:
            raise ValueError("max_drawdown must be between 1% and 50%")
        if self.volatility_lookback < 10:
            raise ValueError("volatility_lookback must be >= 10")


@dataclass
class TechnicalAnalysisConfig:
    """Configuration for technical analysis."""
    atr_period: int = 14
    fib_lookback: int = 50
    atr_multiplier_sl_base: float = 2.0
    atr_multiplier_tp_base: float = 3.0
    volatility_adjustment: bool = True
    trend_confirmation: bool = True
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.atr_period < 5:
            raise ValueError("atr_period must be >= 5")
        if self.fib_lookback < 20:
            raise ValueError("fib_lookback must be >= 20")
        if not 0.5 <= self.atr_multiplier_sl_base <= 5.0:
            raise ValueError("atr_multiplier_sl_base must be between 0.5 and 5.0")
        if not 1.0 <= self.atr_multiplier_tp_base <= 10.0:
            raise ValueError("atr_multiplier_tp_base must be between 1.0 and 10.0")


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""
    cache_duration: int = 30
    parallel_workers: int = 8
    rate_limit_per_second: int = 15
    max_cache_size_mb: float = 50.0
    batch_size: int = 6
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.cache_duration < 5:
            raise ValueError("cache_duration must be >= 5 seconds")
        if not 1 <= self.parallel_workers <= 20:
            raise ValueError("parallel_workers must be between 1 and 20")
        if not 1 <= self.rate_limit_per_second <= 50:
            raise ValueError("rate_limit_per_second must be between 1 and 50")
        if not 1.0 <= self.max_cache_size_mb <= 500.0:
            raise ValueError("max_cache_size_mb must be between 1 and 500 MB")


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breakers."""
    market_data_failure_threshold: int = 3
    market_data_recovery_timeout: float = 30.0
    trading_failure_threshold: int = 2
    trading_recovery_timeout: float = 60.0
    enable_fallbacks: bool = True
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if self.market_data_failure_threshold < 1:
            raise ValueError("market_data_failure_threshold must be >= 1")
        if self.trading_failure_threshold < 1:
            raise ValueError("trading_failure_threshold must be >= 1")
        if self.market_data_recovery_timeout < 10.0:
            raise ValueError("market_data_recovery_timeout must be >= 10 seconds")
        if self.trading_recovery_timeout < 30.0:
            raise ValueError("trading_recovery_timeout must be >= 30 seconds")


@dataclass
class EnhancedBotConfig:
    """Complete enhanced bot configuration with validation."""
    regime_detection: RegimeDetectionConfig = field(default_factory=RegimeDetectionConfig)
    sentiment_analysis: SentimentAnalysisConfig = field(default_factory=SentimentAnalysisConfig)
    decision_engine: DecisionEngineConfig = field(default_factory=DecisionEngineConfig)
    risk_management: RiskManagementConfig = field(default_factory=RiskManagementConfig)
    technical_analysis: TechnicalAnalysisConfig = field(default_factory=TechnicalAnalysisConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    circuit_breakers: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Feature flags
    enable_regime_detection: bool = True
    enable_sentiment_analysis: bool = True
    enable_enhanced_risk: bool = True
    enable_parallel_processing: bool = True
    enable_circuit_breakers: bool = True
    
    def __post_init__(self):
        """Validate cross-component configuration."""
        # Ensure risk management is consistent
        if self.risk_management.max_position_risk > self.risk_management.max_portfolio_risk:
            raise ValueError("max_position_risk cannot exceed max_portfolio_risk")
        
        # Ensure performance settings are reasonable
        if self.performance.batch_size > self.performance.parallel_workers * 2:
            logger.warning(
                "batch_size (%d) is much larger than parallel_workers (%d)",
                self.performance.batch_size, self.performance.parallel_workers
            )
    
    @classmethod
    def from_dict(cls, config_dict: Dict) -> 'EnhancedBotConfig':
        """Create configuration from dictionary with validation."""
        try:
            # Extract nested configurations
            regime_config = RegimeDetectionConfig(**config_dict.get('regime_detection', {}))
            sentiment_config = SentimentAnalysisConfig(**config_dict.get('sentiment_analysis', {}))
            decision_config = DecisionEngineConfig(**config_dict.get('decision_engine', {}))
            risk_config = RiskManagementConfig(**config_dict.get('risk_management', {}))
            technical_config = TechnicalAnalysisConfig(**config_dict.get('technical_analysis', {}))
            performance_config = PerformanceConfig(**config_dict.get('performance', {}))
            circuit_config = CircuitBreakerConfig(**config_dict.get('circuit_breakers', {}))
            
            # Create main configuration
            return cls(
                regime_detection=regime_config,
                sentiment_analysis=sentiment_config,
                decision_engine=decision_config,
                risk_management=risk_config,
                technical_analysis=technical_config,
                performance=performance_config,
                circuit_breakers=circuit_config,
                enable_regime_detection=config_dict.get('enable_regime_detection', True),
                enable_sentiment_analysis=config_dict.get('enable_sentiment_analysis', True),
                enable_enhanced_risk=config_dict.get('enable_enhanced_risk', True),
                enable_parallel_processing=config_dict.get('enable_parallel_processing', True),
                enable_circuit_breakers=config_dict.get('enable_circuit_breakers', True)
            )
            
        except Exception as exc:
            logger.error("Configuration validation failed: %s", exc)
            raise ValueError(f"Invalid configuration: {exc}")
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary."""
        return {
            'regime_detection': self.regime_detection.__dict__,
            'sentiment_analysis': self.sentiment_analysis.__dict__,
            'decision_engine': self.decision_engine.__dict__,
            'risk_management': self.risk_management.__dict__,
            'technical_analysis': self.technical_analysis.__dict__,
            'performance': self.performance.__dict__,
            'circuit_breakers': self.circuit_breakers.__dict__,
            'enable_regime_detection': self.enable_regime_detection,
            'enable_sentiment_analysis': self.enable_sentiment_analysis,
            'enable_enhanced_risk': self.enable_enhanced_risk,
            'enable_parallel_processing': self.enable_parallel_processing,
            'enable_circuit_breakers': self.enable_circuit_breakers
        }
    
    def validate_runtime_constraints(self) -> List[str]:
        """Validate runtime constraints and return warnings."""
        warnings = []
        
        # Check if confidence threshold is too high
        if self.decision_engine.min_confidence_threshold > 0.8:
            warnings.append("Very high confidence threshold may result in few trades")
        
        # Check if risk limits are too conservative
        if self.risk_management.max_position_risk < 0.001:
            warnings.append("Very low position risk may result in tiny position sizes")
        
        # Check if cache duration is too short
        if self.performance.cache_duration < 15:
            warnings.append("Short cache duration may increase API load")
        
        # Check if parallel workers are too many
        if self.performance.parallel_workers > 12:
            warnings.append("High parallel worker count may overwhelm API rate limits")
        
        return warnings


def load_enhanced_config(config_file: Optional[str] = None) -> EnhancedBotConfig:
    """Load enhanced configuration from file or use defaults."""
    if config_file:
        try:
            import json
            with open(config_file, 'r') as f:
                config_dict = json.load(f)
            
            config = EnhancedBotConfig.from_dict(config_dict)
            logger.info("Loaded enhanced configuration from %s", config_file)
            
        except Exception as exc:
            logger.warning("Failed to load config file %s: %s, using defaults", config_file, exc)
            config = EnhancedBotConfig()
    else:
        config = EnhancedBotConfig()
        logger.info("Using default enhanced configuration")
    
    # Validate runtime constraints
    warnings = config.validate_runtime_constraints()
    for warning in warnings:
        logger.warning("Configuration warning: %s", warning)
    
    return config
