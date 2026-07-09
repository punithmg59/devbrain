"""
Caching layer for expensive repository lookups.

Provides TTL-based caching for repository data, evidence, and graph operations.
"""

import hashlib
import json
import logging
import time
from typing import Optional, Any, Dict, Callable
from functools import wraps

from app.utils.logging_config import get_logger
from app.utils.exceptions import CacheError

logger = get_logger(__name__)


class CacheEntry:
    """Cache entry with TTL."""
    
    def __init__(self, value: Any, ttl_seconds: int):
        """
        Initialize cache entry.
        
        Args:
            value: Cached value
            ttl_seconds: Time to live in seconds
        """
        self.value = value
        self.expires_at = time.time() + ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > self.expires_at


class RepositoryCache:
    """
    In-memory cache for repository data and expensive operations.
    
    Provides TTL-based caching with automatic expiration.
    Thread-safe for basic operations.
    """
    
    def __init__(self, default_ttl_seconds: int = 300):
        """
        Initialize repository cache.
        
        Args:
            default_ttl_seconds: Default TTL for cache entries (5 minutes)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl_seconds
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
        logger.info(f"RepositoryCache initialized with default TTL={default_ttl_seconds}s")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:32]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        entry = self._cache.get(key)
        
        if entry is None:
            self._stats["misses"] += 1
            logger.debug(f"Cache miss: {key}")
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self._stats["evictions"] += 1
            logger.debug(f"Cache eviction (expired): {key}")
            return None
        
        self._stats["hits"] += 1
        logger.debug(f"Cache hit: {key}")
        return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (uses default if not provided)
        """
        ttl = ttl_seconds or self._default_ttl
        entry = CacheEntry(value, ttl)
        self._cache[key] = entry
        logger.debug(f"Cache set: {key} (TTL={ttl}s)")
    
    def invalidate(self, key: str):
        """
        Invalidate specific cache entry.
        
        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated: {key}")
    
    def clear(self):
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0.0
        
        return {
            **self._stats,
            "size": len(self._cache),
            "hit_rate": hit_rate
        }
    
    def cleanup_expired(self):
        """Remove all expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats["evictions"] += 1
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global cache instance
_repository_cache = RepositoryCache()


def get_repository_cache() -> RepositoryCache:
    """Get the global repository cache instance."""
    return _repository_cache


def cached(ttl_seconds: Optional[int] = None, key_prefix: Optional[str] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Custom TTL for cached results
        key_prefix: Prefix for cache key
        
    Example:
        @cached(ttl_seconds=600, key_prefix="repo_data")
        def collect_repository_data(repo_id):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_repository_cache()
            
            # Generate cache key
            key_parts = [key_prefix] if key_prefix else []
            key_parts.append(func.__name__)
            key = cache._generate_key(*key_parts, *args, **kwargs)
            
            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                cache.set(key, result, ttl_seconds)
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise CacheError(f"Cached function failed: {e}") from e
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Pattern to match (simple substring match)
    """
    cache = get_repository_cache()
    keys_to_invalidate = [
        key for key in cache._cache.keys()
        if pattern in key
    ]
    
    for key in keys_to_invalidate:
        cache.invalidate(key)
    
    logger.info(f"Invalidated {len(keys_to_invalidate)} cache entries matching pattern: {pattern}")
