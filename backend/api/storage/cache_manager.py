"""
In-memory cache manager with TTL and LRU eviction.
Redis-like functionality without external dependencies.
"""

import time
import threading
from typing import Any, Dict, Optional
from datetime import datetime, timedelta
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Thread-safe in-memory cache with TTL and LRU eviction.
    
    Features:
    - TTL-based expiration
    - LRU eviction when max_size reached
    - Thread-safe operations
    - Periodic cleanup
    """
    
    def __init__(self, ttl_hours: int = 24, max_size: int = 1000):
        """
        Initialize cache manager.
        
        Args:
            ttl_hours: Time-to-live for cached items in hours
            max_size: Maximum number of items to cache
        """
        self.ttl_hours = ttl_hours
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._lock = threading.RLock()
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        
        logger.info(f"CacheManager initialized (TTL: {ttl_hours}h, Max: {max_size})")
    
    def set(self, key: str, value: Any, ttl_hours: Optional[int] = None) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl_hours: Override default TTL
        """
        with self._lock:
            ttl = ttl_hours if ttl_hours is not None else self.ttl_hours
            expires_at = datetime.now() + timedelta(hours=ttl)
            
            # Remove if exists (to update order)
            if key in self._cache:
                del self._cache[key]
            
            # Add to end (most recently used)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": datetime.now()
            }
            
            # Evict oldest if over max_size
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Evicted oldest item: {oldest_key}")
            
            logger.debug(f"Cached item: {key} (expires: {expires_at})")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None
            
            item = self._cache[key]
            
            # Check expiration
            if datetime.now() > item["expires_at"]:
                del self._cache[key]
                logger.debug(f"Item expired: {key}")
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            
            return item["value"]
    
    def delete(self, key: str) -> bool:
        """
        Delete item from cache.
        
        Args:
            key: Cache key
        
        Returns:
            True if deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Deleted item: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared cache ({count} items)")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total = len(self._cache)
            expired_count = sum(
                1 for item in self._cache.values()
                if datetime.now() > item["expires_at"]
            )
            
            return {
                "total_items": total,
                "max_size": self.max_size,
                "expired_items": expired_count,
                "active_items": total - expired_count,
                "usage_percent": (total / self.max_size * 100) if self.max_size > 0 else 0
            }
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired items.
        
        Returns:
            Number of items removed
        """
        with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, item in self._cache.items()
                if now > item["expires_at"]
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired items")
            
            return len(expired_keys)
    
    def start_cleanup_thread(self, interval_minutes: int = 60) -> None:
        """
        Start background thread for periodic cleanup.
        
        Args:
            interval_minutes: Cleanup interval in minutes
        """
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            logger.warning("Cleanup thread already running")
            return
        
        def cleanup_loop():
            while not self._stop_cleanup.wait(interval_minutes * 60):
                try:
                    self.cleanup_expired()
                except Exception as e:
                    logger.error(f"Cleanup error: {e}")
        
        self._cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        logger.info(f"Started cleanup thread (interval: {interval_minutes}min)")
    
    def stop_cleanup_thread(self) -> None:
        """Stop background cleanup thread."""
        if self._cleanup_thread:
            self._stop_cleanup.set()
            self._cleanup_thread.join(timeout=5)
            logger.info("Stopped cleanup thread")
