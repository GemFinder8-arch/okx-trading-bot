"""Circuit breaker pattern for resilient API calls and graceful degradation."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    recovery_timeout: float = 60.0      # Seconds before trying half-open
    success_threshold: int = 3          # Successes to close from half-open
    timeout: float = 30.0               # Request timeout
    expected_exception: type = Exception  # Exception type to count as failure


@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failure_count: int
    success_count: int
    total_requests: int
    last_failure_time: Optional[float]
    state_change_time: float
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failure_count / self.total_requests) * 100
    
    @property
    def uptime_seconds(self) -> float:
        """Get uptime since last state change."""
        return time.time() - self.state_change_time


class CircuitBreaker:
    """Circuit breaker for resilient service calls."""
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        """Initialize circuit breaker.
        
        Args:
            name: Circuit breaker name for logging
            config: Configuration object
        """
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.last_failure_time: Optional[float] = None
        self.state_change_time = time.time()
        
        # Fallback functions
        self.fallback_func: Optional[Callable] = None
        
        logger.info(
            "Initialized circuit breaker '%s': threshold=%d, timeout=%.1fs",
            name, self.config.failure_threshold, self.config.recovery_timeout
        )
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
            
        Raises:
            Exception: If circuit is open and no fallback available
        """
        self.total_requests += 1
        
        # Check if circuit is open
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                return self._handle_open_circuit(func, *args, **kwargs)
        
        # Attempt to call function
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Check for timeout
            if execution_time > self.config.timeout:
                raise TimeoutError(f"Function execution exceeded {self.config.timeout}s")
            
            self._on_success()
            return result
            
        except self.config.expected_exception as exc:
            self._on_failure(exc)
            return self._handle_failure(func, exc, *args, **kwargs)
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from open state."""
        if self.last_failure_time is None:
            return True
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_change_time = time.time()
        
        logger.info("Circuit breaker '%s' transitioned to HALF_OPEN", self.name)
    
    def _on_success(self) -> None:
        """Handle successful function execution."""
        self.success_count += 1
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self, exception: Exception) -> None:
        """Handle failed function execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        logger.warning(
            "Circuit breaker '%s' recorded failure (%d/%d): %s",
            self.name, self.failure_count, self.config.failure_threshold, exception
        )
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self._transition_to_open()
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
    
    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_change_time = time.time()
        
        logger.info("Circuit breaker '%s' transitioned to CLOSED", self.name)
    
    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.state_change_time = time.time()
        
        logger.warning("Circuit breaker '%s' transitioned to OPEN", self.name)
    
    def _handle_open_circuit(self, func: Callable, *args, **kwargs) -> Any:
        """Handle call when circuit is open."""
        if self.fallback_func:
            logger.debug("Circuit breaker '%s' using fallback function", self.name)
            return self.fallback_func(*args, **kwargs)
        
        raise Exception(f"Circuit breaker '{self.name}' is OPEN - service unavailable")
    
    def _handle_failure(self, func: Callable, exception: Exception, *args, **kwargs) -> Any:
        """Handle function failure."""
        if self.fallback_func:
            logger.debug("Circuit breaker '%s' using fallback after failure", self.name)
            return self.fallback_func(*args, **kwargs)
        
        raise exception
    
    def set_fallback(self, fallback_func: Callable) -> None:
        """Set fallback function for when circuit is open or calls fail.
        
        Args:
            fallback_func: Function to call as fallback
        """
        self.fallback_func = fallback_func
        logger.info("Circuit breaker '%s' fallback function set", self.name)
    
    def force_open(self) -> None:
        """Force circuit breaker to open state."""
        self._transition_to_open()
        logger.warning("Circuit breaker '%s' forced to OPEN state", self.name)
    
    def force_close(self) -> None:
        """Force circuit breaker to closed state."""
        self._transition_to_closed()
        logger.info("Circuit breaker '%s' forced to CLOSED state", self.name)
    
    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.last_failure_time = None
        self.state_change_time = time.time()
        
        logger.info("Circuit breaker '%s' reset to initial state", self.name)
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics.
        
        Returns:
            CircuitBreakerStats object
        """
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self.failure_count,
            success_count=self.success_count,
            total_requests=self.total_requests,
            last_failure_time=self.last_failure_time,
            state_change_time=self.state_change_time
        )


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.breakers: Dict[str, CircuitBreaker] = {}
    
    def get_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Configuration for new breaker
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name, config)
        
        return self.breakers[name]
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers.
        
        Returns:
            Dictionary mapping breaker names to their stats
        """
        return {name: breaker.get_stats() for name, breaker in self.breakers.items()}
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()
        
        logger.info("All circuit breakers reset")
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary of all circuit breakers.
        
        Returns:
            Health summary dictionary
        """
        stats = self.get_all_stats()
        
        total_breakers = len(stats)
        open_breakers = sum(1 for s in stats.values() if s.state == CircuitState.OPEN)
        half_open_breakers = sum(1 for s in stats.values() if s.state == CircuitState.HALF_OPEN)
        
        return {
            "total_breakers": total_breakers,
            "healthy_breakers": total_breakers - open_breakers - half_open_breakers,
            "open_breakers": open_breakers,
            "half_open_breakers": half_open_breakers,
            "overall_health": "healthy" if open_breakers == 0 else "degraded" if open_breakers < total_breakers else "critical"
        }


# Global circuit breaker manager
_global_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker.
    
    Args:
        name: Circuit breaker name
        config: Configuration for new breaker
        
    Returns:
        CircuitBreaker instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = CircuitBreakerManager()
    
    return _global_manager.get_breaker(name, config)


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """Get global circuit breaker manager.
    
    Returns:
        CircuitBreakerManager instance
    """
    global _global_manager
    
    if _global_manager is None:
        _global_manager = CircuitBreakerManager()
    
    return _global_manager
