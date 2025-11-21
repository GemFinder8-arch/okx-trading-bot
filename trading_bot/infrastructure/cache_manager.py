"""Advanced caching system with memory management and persistence."""

from __future__ import annotations

import json
import logging
import pickle
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    accessed_at: float
    access_count: int
    ttl_seconds: Optional[float]
    size_bytes: int
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() - self.created_at > self.ttl_seconds
    
    def is_stale(self, max_age_seconds: float) -> bool:
        """Check if cache entry is stale."""
        return time.time() - self.accessed_at > max_age_seconds


@dataclass
class CacheStats:
    """Cache performance statistics."""
    total_entries: int
    total_size_bytes: int
    hit_count: int
    miss_count: int
    eviction_count: int
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_requests = self.hit_count + self.miss_count
        return (self.hit_count / total_requests * 100) if total_requests > 0 else 0.0
    
    @property
    def size_mb(self) -> float:
        """Get cache size in MB."""
        return self.total_size_bytes / (1024 * 1024)


class AdvancedCacheManager:
    """Advanced caching system with LRU eviction, persistence, and memory management."""
    
    def __init__(
        self,
        max_size_mb: float = 100.0,
        max_entries: int = 10000,
        default_ttl_seconds: float = 300.0,  # 5 minutes
        persistence_path: Optional[str] = None,
        auto_cleanup_interval: float = 60.0  # 1 minute
    ):
        """Initialize cache manager.
        
        Args:
            max_size_mb: Maximum cache size in MB
            max_entries: Maximum number of cache entries
            default_ttl_seconds: Default TTL for cache entries
            persistence_path: Path for cache persistence (optional)
            auto_cleanup_interval: Interval for automatic cleanup in seconds
        """
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_entries = max_entries
        self.default_ttl_seconds = default_ttl_seconds
        self.persistence_path = Path(persistence_path) if persistence_path else None
        self.auto_cleanup_interval = auto_cleanup_interval
        
        # Cache storage
        self._cache: Dict[str, CacheEntry] = {}
        
        # Statistics
        self._stats = CacheStats(0, 0, 0, 0, 0)
        self._last_cleanup = time.time()
        
        # Load persisted cache if available
        self._load_persistent_cache()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            default: Default value if key not found
            
        Returns:
            Cached value or default
        """
        self._maybe_cleanup()
        
        if key not in self._cache:
            self._stats.miss_count += 1
            return default
        
        entry = self._cache[key]
        
        # Check if expired
        if entry.is_expired():
            del self._cache[key]
            self._stats.miss_count += 1
            self._stats.eviction_count += 1
            return default
        
        # Update access metadata
        entry.accessed_at = time.time()
        entry.access_count += 1
        
        self._stats.hit_count += 1
        return entry.value
    
    def set(
        self, 
        key: str, 
        value: Any, 
        ttl_seconds: Optional[float] = None
    ) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (uses default if None)
            
        Returns:
            True if successfully cached, False otherwise
        """
        self._maybe_cleanup()
        
        # Calculate size
        try:
            size_bytes = len(pickle.dumps(value))
        except Exception:
            # Fallback size estimation
            size_bytes = len(str(value)) * 2
        
        # Check if value is too large
        if size_bytes > self.max_size_bytes * 0.1:  # Max 10% of total cache size
            logger.warning("Value too large to cache: %d bytes", size_bytes)
            return False
        
        # Ensure we have space
        if not self._ensure_space(size_bytes):
            logger.warning("Could not make space for cache entry: %s", key)
            return False
        
        # Create cache entry
        current_time = time.time()
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=current_time,
            accessed_at=current_time,
            access_count=1,
            ttl_seconds=ttl,
            size_bytes=size_bytes
        )
        
        # Remove old entry if exists
        if key in self._cache:
            old_entry = self._cache[key]
            self._stats.total_size_bytes -= old_entry.size_bytes
            self._stats.total_entries -= 1
        
        # Add new entry
        self._cache[key] = entry
        self._stats.total_entries += 1
        self._stats.total_size_bytes += size_bytes
        
        return True
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        if key not in self._cache:
            return False
        
        entry = self._cache[key]
        del self._cache[key]
        
        self._stats.total_entries -= 1
        self._stats.total_size_bytes -= entry.size_bytes
        self._stats.eviction_count += 1
        
        return True
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._stats = CacheStats(0, 0, self._stats.hit_count, self._stats.miss_count, self._stats.eviction_count)
    
    def _ensure_space(self, required_bytes: int) -> bool:
        """Ensure there's enough space for a new entry."""
        # Check entry count limit
        while len(self._cache) >= self.max_entries:
            if not self._evict_lru():
                return False
        
        # Check size limit
        while (self._stats.total_size_bytes + required_bytes) > self.max_size_bytes:
            if not self._evict_lru():
                return False
        
        return True
    
    def _evict_lru(self) -> bool:
        """Evict least recently used entry."""
        if not self._cache:
            return False
        
        # Find LRU entry
        lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].accessed_at)
        
        # Remove it
        entry = self._cache[lru_key]
        del self._cache[lru_key]
        
        self._stats.total_entries -= 1
        self._stats.total_size_bytes -= entry.size_bytes
        self._stats.eviction_count += 1
        
        logger.debug("Evicted LRU cache entry: %s", lru_key)
        return True
    
    def _maybe_cleanup(self) -> None:
        """Perform cleanup if needed."""
        current_time = time.time()
        if current_time - self._last_cleanup > self.auto_cleanup_interval:
            self.cleanup()
            self._last_cleanup = current_time
    
    def cleanup(self) -> int:
        """Clean up expired and stale entries.
        
        Returns:
            Number of entries cleaned up
        """
        current_time = time.time()
        keys_to_remove = []
        
        for key, entry in self._cache.items():
            if entry.is_expired() or entry.is_stale(self.auto_cleanup_interval * 10):
                keys_to_remove.append(key)
        
        # Remove expired/stale entries
        for key in keys_to_remove:
            self.delete(key)
        
        logger.debug("Cache cleanup removed %d entries", len(keys_to_remove))
        return len(keys_to_remove)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return CacheStats(
            total_entries=len(self._cache),
            total_size_bytes=self._stats.total_size_bytes,
            hit_count=self._stats.hit_count,
            miss_count=self._stats.miss_count,
            eviction_count=self._stats.eviction_count
        )
    
    def _load_persistent_cache(self) -> None:
        """Load cache from persistent storage."""
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        try:
            with open(self.persistence_path, 'rb') as f:
                data = pickle.load(f)
                
            # Validate and load entries
            loaded_count = 0
            for key, entry_data in data.items():
                try:
                    entry = CacheEntry(**entry_data)
                    if not entry.is_expired():
                        self._cache[key] = entry
                        self._stats.total_entries += 1
                        self._stats.total_size_bytes += entry.size_bytes
                        loaded_count += 1
                except Exception as exc:
                    logger.warning("Failed to load cache entry %s: %s", key, exc)
            
            logger.info("Loaded %d cache entries from persistent storage", loaded_count)
            
        except Exception as exc:
            logger.warning("Failed to load persistent cache: %s", exc)
    
    def save_persistent_cache(self) -> bool:
        """Save cache to persistent storage.
        
        Returns:
            True if successfully saved, False otherwise
        """
        if not self.persistence_path:
            return False
        
        try:
            # Prepare data for serialization
            data = {}
            for key, entry in self._cache.items():
                if not entry.is_expired():
                    data[key] = asdict(entry)
            
            # Ensure directory exists
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(self.persistence_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.info("Saved %d cache entries to persistent storage", len(data))
            return True
            
        except Exception as exc:
            logger.error("Failed to save persistent cache: %s", exc)
            return False
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get detailed memory usage statistics.
        
        Returns:
            Dictionary with memory usage details in MB
        """
        stats = self.get_stats()
        
        return {
            "total_size_mb": stats.size_mb,
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "utilization_pct": (stats.total_size_bytes / self.max_size_bytes) * 100,
            "entries_count": stats.total_entries,
            "max_entries": self.max_entries,
            "avg_entry_size_kb": (stats.total_size_bytes / stats.total_entries / 1024) if stats.total_entries > 0 else 0
        }


# Global cache instances
_global_caches: Dict[str, AdvancedCacheManager] = {}


def get_cache(name: str, **kwargs) -> AdvancedCacheManager:
    """Get or create a named cache instance.
    
    Args:
        name: Cache name
        **kwargs: Arguments for cache creation
        
    Returns:
        AdvancedCacheManager instance
    """
    if name not in _global_caches:
        _global_caches[name] = AdvancedCacheManager(**kwargs)
    
    return _global_caches[name]


def clear_all_caches() -> None:
    """Clear all global caches."""
    for cache in _global_caches.values():
        cache.clear()


def save_all_caches() -> None:
    """Save all persistent caches."""
    for cache in _global_caches.values():
        cache.save_persistent_cache()
