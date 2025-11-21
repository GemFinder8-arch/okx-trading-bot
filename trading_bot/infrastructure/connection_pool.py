"""Connection pool manager for optimized API connections."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional
from urllib3 import PoolManager
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Connection pool statistics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    total_requests: int
    failed_requests: int
    avg_response_time: float
    
    @property
    def success_rate(self) -> float:
        """Calculate request success rate."""
        if self.total_requests == 0:
            return 100.0
        return ((self.total_requests - self.failed_requests) / self.total_requests) * 100


class ConnectionPoolManager:
    """Manages HTTP connection pools for API efficiency."""
    
    def __init__(
        self,
        max_pool_size: int = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.3,
        timeout: float = 30.0,
        keep_alive: bool = True
    ):
        """Initialize connection pool manager.
        
        Args:
            max_pool_size: Maximum number of connections in pool
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
            timeout: Request timeout in seconds
            keep_alive: Whether to keep connections alive
        """
        self.max_pool_size = max_pool_size
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.keep_alive = keep_alive
        
        # Statistics tracking
        self.total_requests = 0
        self.failed_requests = 0
        self.response_times = []
        
        # Create retry strategy
        self.retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        # Create connection pool
        self.pool = PoolManager(
            num_pools=max_pool_size,
            maxsize=max_pool_size,
            retries=self.retry_strategy,
            timeout=timeout,
            headers={
                'Connection': 'keep-alive' if keep_alive else 'close',
                'User-Agent': 'TradingBot/1.0'
            }
        )
        
        logger.info(
            "Initialized connection pool: max_size=%d, timeout=%.1fs, retries=%d",
            max_pool_size, timeout, max_retries
        )
    
    def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[str] = None,
        **kwargs
    ) -> Optional[any]:
        """Make HTTP request using connection pool.
        
        Args:
            method: HTTP method
            url: Request URL
            headers: Additional headers
            body: Request body
            **kwargs: Additional arguments
            
        Returns:
            Response object or None if failed
        """
        start_time = time.time()
        self.total_requests += 1
        
        try:
            # Merge headers
            request_headers = {'Content-Type': 'application/json'}
            if headers:
                request_headers.update(headers)
            
            # Make request
            response = self.pool.request(
                method=method,
                url=url,
                headers=request_headers,
                body=body,
                **kwargs
            )
            
            # Track response time
            response_time = time.time() - start_time
            self.response_times.append(response_time)
            
            # Keep only recent response times (last 1000)
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
            
            return response
            
        except Exception as exc:
            self.failed_requests += 1
            response_time = time.time() - start_time
            
            logger.warning(
                "Request failed: %s %s (%.3fs) - %s",
                method, url, response_time, exc
            )
            return None
    
    def get_stats(self) -> ConnectionStats:
        """Get connection pool statistics.
        
        Returns:
            ConnectionStats object
        """
        # Calculate average response time
        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
        
        return ConnectionStats(
            total_connections=self.max_pool_size,
            active_connections=0,  # urllib3 doesn't expose this easily
            idle_connections=0,    # urllib3 doesn't expose this easily
            total_requests=self.total_requests,
            failed_requests=self.failed_requests,
            avg_response_time=avg_response_time
        )
    
    def health_check(self, test_url: str = "https://httpbin.org/status/200") -> bool:
        """Perform health check on connection pool.
        
        Args:
            test_url: URL to test connectivity
            
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.request("GET", test_url)
            return response is not None and response.status == 200
        except Exception:
            return False
    
    def reset_stats(self) -> None:
        """Reset statistics counters."""
        self.total_requests = 0
        self.failed_requests = 0
        self.response_times = []
        logger.info("Connection pool statistics reset")
    
    def close(self) -> None:
        """Close connection pool and cleanup resources."""
        try:
            self.pool.clear()
            logger.info("Connection pool closed")
        except Exception as exc:
            logger.warning("Error closing connection pool: %s", exc)


# Global connection pool instance
_global_pool: Optional[ConnectionPoolManager] = None


def get_connection_pool(**kwargs) -> ConnectionPoolManager:
    """Get or create global connection pool.
    
    Args:
        **kwargs: Arguments for pool creation
        
    Returns:
        ConnectionPoolManager instance
    """
    global _global_pool
    
    if _global_pool is None:
        _global_pool = ConnectionPoolManager(**kwargs)
    
    return _global_pool


def close_global_pool() -> None:
    """Close global connection pool."""
    global _global_pool
    
    if _global_pool:
        _global_pool.close()
        _global_pool = None
