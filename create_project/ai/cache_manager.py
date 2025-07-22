# ABOUTME: LRU cache system for AI responses with TTL expiration and JSON persistence
# ABOUTME: Thread-safe operations with configurable size limits and automatic cleanup

"""LRU cache management system for AI response caching.

This module provides a sophisticated caching system for AI responses with
Least Recently Used (LRU) eviction, Time To Live (TTL) expiration, and
persistent storage capabilities. It's designed for high-performance caching
of AI model responses to reduce latency and API calls.

Key Features:
    - LRU (Least Recently Used) eviction policy for memory efficiency
    - TTL expiration with configurable per-entry lifetimes
    - Thread-safe operations using RLock for concurrent access
    - JSON file persistence with atomic write operations
    - Automatic cache key generation from request parameters
    - Comprehensive statistics tracking (hits, misses, evictions)
    - Auto-persistence with configurable intervals
    - Cache file rotation to prevent unbounded growth
    - Expired entry cleanup and size estimation

Main Classes:
    - CacheEntry: Individual cache entry with metadata and access tracking
    - CacheStats: Statistics tracking for cache performance monitoring
    - ResponseCacheManager: Main cache manager with full lifecycle support

Usage Example:
    ```python
    from create_project.ai.cache_manager import ResponseCacheManager
    from datetime import timedelta

    # Initialize cache manager
    cache = ResponseCacheManager(
        max_size=100,  # Maximum 100 entries
        default_ttl_hours=24,  # 24 hour TTL
        auto_persist=True,  # Auto-save to disk
        persist_interval=300  # Save every 5 minutes
    )

    # Generate cache key from parameters
    key = cache.generate_key(
        model="llama2:7b",
        prompt="Explain Python decorators",
        temperature=0.7
    )

    # Check cache
    cached_response = cache.get(key)
    if cached_response is None:
        # Generate response (expensive operation)
        response = generate_ai_response(...)

        # Store in cache with custom TTL
        cache.put(key, response, ttl=timedelta(hours=12))

    # Get cache statistics
    stats = cache.get_stats()
    print(f"Cache hit rate: {stats.hit_rate:.1f}%")
    print(f"Cache fill rate: {stats.fill_rate:.1f}%")

    # Cleanup expired entries
    expired_count = cache.cleanup_expired()
    print(f"Removed {expired_count} expired entries")

    # Persist cache to disk
    cache.persist()
    ```

The cache manager automatically handles file persistence, creating cache files
in the user's cache directory (platform-specific) and supports cache file
rotation to prevent unlimited growth.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import structlog
from platformdirs import user_cache_dir

from .exceptions import CacheError

logger = structlog.get_logger(__name__)


@dataclass
class CacheEntry:
    """A single cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now() >= self.expires_at

    def is_valid(self) -> bool:
        """Check if the cache entry is valid (not expired)."""
        return not self.is_expired()

    def access(self) -> None:
        """Record an access to this cache entry."""
        self.access_count += 1
        self.last_accessed = datetime.now()


@dataclass
class CacheStats:
    """Cache statistics for monitoring and optimization."""

    total_entries: int = 0
    max_size: int = 0
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired_entries: int = 0
    total_size_bytes: int = 0
    cache_file_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as a percentage."""
        total_requests = self.hits + self.misses
        return (self.hits / total_requests * 100) if total_requests > 0 else 0.0

    @property
    def fill_rate(self) -> float:
        """Calculate cache fill rate as a percentage."""
        return (self.total_entries / self.max_size * 100) if self.max_size > 0 else 0.0


class ResponseCacheManager:
    """
    LRU cache manager for AI responses with TTL expiration and JSON persistence.

    Features:
    - LRU (Least Recently Used) eviction policy
    - TTL (Time To Live) expiration with 24-hour default
    - Thread-safe operations with RLock
    - JSON file persistence in user cache directory
    - Cache key generation from request parameters
    - Cache statistics and monitoring
    - Automatic cleanup and file rotation
    """

    def __init__(
        self,
        max_size: int = 100,
        default_ttl_hours: int = 24,
        cache_dir: Optional[Path] = None,
        cache_filename: str = "ai_responses.json",
        auto_persist: bool = True,
        persist_interval: int = 300,
    ):  # 5 minutes
        """
        Initialize the response cache manager.

        Args:
            max_size: Maximum number of cache entries
            default_ttl_hours: Default TTL for entries in hours
            cache_dir: Directory for cache files (default: platformdirs cache)
            cache_filename: Name of cache file
            auto_persist: Whether to auto-persist cache changes
            persist_interval: Interval between auto-persist operations (seconds)
        """
        self.max_size = max_size
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.auto_persist = auto_persist
        self.persist_interval = persist_interval

        # Set up cache directory
        if cache_dir is None:
            self.cache_dir = Path(user_cache_dir("create-project", "claude")) / "ai"
        else:
            self.cache_dir = Path(cache_dir)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / cache_filename

        # Thread safety
        self._lock = threading.RLock()

        # Cache storage - OrderedDict for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self._stats = CacheStats(max_size=max_size)

        # Persistence tracking
        self._last_persist_time = time.time()
        self._dirty = False

        # Load existing cache
        self._load_cache()

        logger.info(
            "Cache manager initialized",
            max_size=max_size,
            cache_dir=str(self.cache_dir),
            cache_file=str(self.cache_file),
            existing_entries=len(self._cache),
        )

    def generate_key(self, **params: Any) -> str:
        """
        Generate a cache key from request parameters.

        Args:
            **params: Request parameters to hash

        Returns:
            SHA-256 hash of the sorted parameters
        """
        # Create a sorted, JSON-serializable representation
        key_data = {}
        for k, v in sorted(params.items()):
            if isinstance(v, (dict, list)):
                key_data[k] = json.dumps(v, sort_keys=True)
            else:
                key_data[k] = str(v)

        # Generate hash
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                logger.debug("Cache miss", key=key[:16])
                return None

            if entry.is_expired():
                logger.debug("Cache entry expired", key=key[:16])
                self._remove_entry(key)
                self._stats.misses += 1
                self._stats.expired_entries += 1
                return None

            # Update access info and move to end (most recently used)
            entry.access()
            self._cache.move_to_end(key)
            self._stats.hits += 1
            self._mark_dirty()

            logger.debug("Cache hit", key=key[:16], access_count=entry.access_count)
            return entry.value

    def put(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live (default: configured default_ttl)
        """
        if ttl is None:
            ttl = self.default_ttl

        with self._lock:
            now = datetime.now()
            expires_at = now + ttl

            # Create new entry
            entry = CacheEntry(
                key=key, value=value, created_at=now, expires_at=expires_at
            )

            # If key already exists, remove old entry
            if key in self._cache:
                del self._cache[key]

            # Add new entry
            self._cache[key] = entry
            self._cache.move_to_end(key)  # Mark as most recently used

            # Check if we need to evict entries
            self._evict_if_needed()

            self._mark_dirty()
            self._auto_persist_if_needed()

            logger.debug("Cache put", key=key[:16], expires_in=ttl.total_seconds())

    def delete(self, key: str) -> bool:
        """
        Remove an entry from the cache.

        Args:
            key: Cache key to remove

        Returns:
            True if entry was removed, False if not found
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                self._mark_dirty()
                logger.debug("Cache delete", key=key[:16])
                return True
            return False

    def clear(self) -> int:
        """
        Clear all entries from the cache.

        Returns:
            Number of entries cleared
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.total_entries = 0
            self._mark_dirty()
            logger.info("Cache cleared", entries_removed=count)
            return count

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of expired entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items() if entry.is_expired()
            ]

            for key in expired_keys:
                self._remove_entry(key)
                self._stats.expired_entries += 1

            if expired_keys:
                self._mark_dirty()
                logger.info("Expired entries cleaned up", count=len(expired_keys))

            return len(expired_keys)

    def get_stats(self) -> CacheStats:
        """Get current cache statistics."""
        with self._lock:
            # Update current stats
            self._stats.total_entries = len(self._cache)
            self._stats.total_size_bytes = self._estimate_cache_size()

            if self.cache_file.exists():
                self._stats.cache_file_size = self.cache_file.stat().st_size

            return self._stats

    def persist(self, force: bool = False) -> bool:
        """
        Persist cache to disk.

        Args:
            force: Force persist even if cache is clean

        Returns:
            True if persisted, False if no changes or error
        """
        with self._lock:
            if not (self._dirty or force):
                return False

            try:
                # Prepare data for serialization
                cache_data = {
                    "version": "1.0",
                    "created": datetime.now().isoformat(),
                    "stats": asdict(self._stats),
                    "entries": {},
                }

                # Convert entries to serializable format
                for key, entry in self._cache.items():
                    cache_data["entries"][key] = {
                        "key": entry.key,
                        "value": entry.value,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat(),
                        "access_count": entry.access_count,
                        "last_accessed": entry.last_accessed.isoformat()
                        if entry.last_accessed
                        else None,
                    }

                # Write to temporary file first, then rename (atomic operation)
                temp_file = self.cache_file.with_suffix(".tmp")
                with temp_file.open("w", encoding="utf-8") as f:
                    json.dump(cache_data, f, indent=2)

                temp_file.rename(self.cache_file)

                self._dirty = False
                self._last_persist_time = time.time()

                logger.debug("Cache persisted", entries=len(self._cache))
                return True

            except Exception as e:
                logger.error("Failed to persist cache", error=str(e), exc_info=True)
                raise CacheError(f"Failed to persist cache: {e}")

    def _load_cache(self) -> None:
        """Load cache from disk."""
        if not self.cache_file.exists():
            logger.debug("No existing cache file found")
            return

        try:
            with self.cache_file.open("r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Load entries
            loaded_count = 0
            expired_count = 0

            for key, entry_data in cache_data.get("entries", {}).items():
                try:
                    entry = CacheEntry(
                        key=entry_data["key"],
                        value=entry_data["value"],
                        created_at=datetime.fromisoformat(entry_data["created_at"]),
                        expires_at=datetime.fromisoformat(entry_data["expires_at"]),
                        access_count=entry_data.get("access_count", 0),
                        last_accessed=datetime.fromisoformat(
                            entry_data["last_accessed"]
                        )
                        if entry_data.get("last_accessed")
                        else None,
                    )

                    if entry.is_valid():
                        self._cache[key] = entry
                        loaded_count += 1
                    else:
                        expired_count += 1

                except (ValueError, KeyError) as e:
                    logger.warning(
                        "Invalid cache entry skipped", key=key[:16], error=str(e)
                    )

            # Load stats if available
            if "stats" in cache_data:
                try:
                    stats_data = cache_data["stats"]
                    self._stats.hits = stats_data.get("hits", 0)
                    self._stats.misses = stats_data.get("misses", 0)
                    self._stats.evictions = stats_data.get("evictions", 0)
                    self._stats.expired_entries = (
                        stats_data.get("expired_entries", 0) + expired_count
                    )
                except Exception as e:
                    logger.warning("Failed to load cache stats", error=str(e))

            logger.info(
                "Cache loaded from disk", loaded=loaded_count, expired=expired_count
            )

        except Exception as e:
            logger.error("Failed to load cache from disk", error=str(e))
            # Continue with empty cache rather than failing

    def _evict_if_needed(self) -> None:
        """Evict least recently used entries if cache is full."""
        while len(self._cache) > self.max_size:
            # Get least recently used key (first item in OrderedDict)
            lru_key = next(iter(self._cache))
            self._remove_entry(lru_key)
            self._stats.evictions += 1
            logger.debug("LRU eviction", evicted_key=lru_key[:16])

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from cache."""
        if key in self._cache:
            del self._cache[key]
            self._stats.total_entries = len(self._cache)

    def _mark_dirty(self) -> None:
        """Mark cache as dirty (needs persistence)."""
        self._dirty = True

    def _auto_persist_if_needed(self) -> None:
        """Auto-persist cache if interval has passed."""
        if not self.auto_persist:
            return

        current_time = time.time()
        if current_time - self._last_persist_time >= self.persist_interval:
            try:
                self.persist()
            except Exception as e:
                logger.warning("Auto-persist failed", error=str(e))

    def _estimate_cache_size(self) -> int:
        """Estimate the size of cache in bytes."""
        try:
            # Rough estimation using JSON serialization
            sample_data = {}
            count = 0
            for key, entry in self._cache.items():
                sample_data[key] = {
                    "value": entry.value,
                    "created_at": entry.created_at.isoformat(),
                    "expires_at": entry.expires_at.isoformat(),
                }
                count += 1
                if count >= 10:  # Sample first 10 entries
                    break

            if sample_data:
                sample_size = len(json.dumps(sample_data))
                estimated_total = int(sample_size * len(self._cache) / len(sample_data))
                return estimated_total

        except Exception:
            pass

        return 0

    def get_cache_info(self) -> Dict[str, Any]:
        """Get detailed cache information."""
        with self._lock:
            info = {
                "config": {
                    "max_size": self.max_size,
                    "default_ttl_hours": self.default_ttl.total_seconds() / 3600,
                    "cache_dir": str(self.cache_dir),
                    "cache_file": str(self.cache_file),
                    "auto_persist": self.auto_persist,
                },
                "stats": asdict(self.get_stats()),
                "entries": [],
            }

            # Add entry information
            for key, entry in self._cache.items():
                entry_info = {
                    "key": key[:16] + "..." if len(key) > 16 else key,
                    "created_at": entry.created_at.isoformat(),
                    "expires_at": entry.expires_at.isoformat(),
                    "expires_in_seconds": int(
                        (entry.expires_at - datetime.now()).total_seconds()
                    ),
                    "access_count": entry.access_count,
                    "last_accessed": entry.last_accessed.isoformat()
                    if entry.last_accessed
                    else None,
                    "is_expired": entry.is_expired(),
                    "value_type": type(entry.value).__name__,
                    "value_size": len(str(entry.value)),
                }
                info["entries"].append(entry_info)

            return info

    def rotate_cache_file(self, backup_count: int = 5) -> bool:
        """
        Rotate cache file when it gets too large.

        Args:
            backup_count: Number of backup files to keep

        Returns:
            True if rotation occurred, False otherwise
        """
        if not self.cache_file.exists():
            return False

        try:
            # Create backup files
            for i in range(backup_count - 1, 0, -1):
                old_backup = self.cache_file.with_suffix(f".{i}")
                new_backup = self.cache_file.with_suffix(f".{i + 1}")

                if old_backup.exists():
                    if new_backup.exists():
                        new_backup.unlink()
                    old_backup.rename(new_backup)

            # Move current file to .1
            backup_file = self.cache_file.with_suffix(".1")
            if backup_file.exists():
                backup_file.unlink()
            self.cache_file.rename(backup_file)

            logger.info("Cache file rotated", backup_file=str(backup_file))
            return True

        except Exception as e:
            logger.error("Cache file rotation failed", error=str(e))
            return False
