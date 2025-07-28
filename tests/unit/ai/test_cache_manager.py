# ABOUTME: Comprehensive unit tests for ResponseCacheManager with LRU eviction and TTL
# ABOUTME: Tests thread safety, persistence, statistics, and edge cases

"""Unit tests for cache manager module."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Thread
from unittest.mock import MagicMock, Mock, patch

import pytest

from create_project.ai.cache_manager import (
    CacheEntry,
    CacheStats,
    ResponseCacheManager,
)
from create_project.ai.exceptions import CacheError


class TestCacheEntry:
    """Test CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        now = datetime.now()
        expires = now + timedelta(hours=1)
        
        entry = CacheEntry(
            key="test_key",
            value={"response": "test"},
            created_at=now,
            expires_at=expires,
        )
        
        assert entry.key == "test_key"
        assert entry.value == {"response": "test"}
        assert entry.created_at == now
        assert entry.expires_at == expires
        assert entry.access_count == 0
        assert entry.last_accessed is None

    def test_cache_entry_expiration(self):
        """Test cache entry expiration checking."""
        now = datetime.now()
        
        # Create expired entry
        expired_entry = CacheEntry(
            key="expired",
            value="data",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1),
        )
        assert expired_entry.is_expired() is True
        assert expired_entry.is_valid() is False
        
        # Create valid entry
        valid_entry = CacheEntry(
            key="valid",
            value="data",
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )
        assert valid_entry.is_expired() is False
        assert valid_entry.is_valid() is True

    def test_cache_entry_access(self):
        """Test recording access to cache entry."""
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
        )
        
        assert entry.access_count == 0
        assert entry.last_accessed is None
        
        # Record access
        entry.access()
        assert entry.access_count == 1
        assert entry.last_accessed is not None
        
        # Record another access
        first_access = entry.last_accessed
        time.sleep(0.01)  # Small delay to ensure different timestamps
        entry.access()
        assert entry.access_count == 2
        assert entry.last_accessed > first_access


class TestCacheStats:
    """Test CacheStats dataclass."""

    def test_cache_stats_initialization(self):
        """Test cache stats initialization."""
        stats = CacheStats(
            total_entries=50,
            max_size=100,
            hits=75,
            misses=25,
        )
        
        assert stats.total_entries == 50
        assert stats.max_size == 100
        assert stats.hits == 75
        assert stats.misses == 25

    def test_hit_rate_calculation(self):
        """Test cache hit rate calculation."""
        # No requests
        stats = CacheStats()
        assert stats.hit_rate == 0.0
        
        # All hits
        stats = CacheStats(hits=100, misses=0)
        assert stats.hit_rate == 100.0
        
        # Mix of hits and misses
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 75.0
        
        # More misses than hits
        stats = CacheStats(hits=20, misses=80)
        assert stats.hit_rate == 20.0

    def test_fill_rate_calculation(self):
        """Test cache fill rate calculation."""
        # Empty cache
        stats = CacheStats(total_entries=0, max_size=100)
        assert stats.fill_rate == 0.0
        
        # Full cache
        stats = CacheStats(total_entries=100, max_size=100)
        assert stats.fill_rate == 100.0
        
        # Partially filled
        stats = CacheStats(total_entries=50, max_size=100)
        assert stats.fill_rate == 50.0
        
        # No max size (edge case)
        stats = CacheStats(total_entries=50, max_size=0)
        assert stats.fill_rate == 0.0


class TestResponseCacheManager:
    """Test ResponseCacheManager class."""

    @pytest.fixture
    def temp_cache_dir(self, tmp_path):
        """Create temporary cache directory."""
        cache_dir = tmp_path / "test_cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir

    @pytest.fixture
    def cache_manager(self, temp_cache_dir):
        """Create cache manager instance for testing."""
        return ResponseCacheManager(
            max_size=5,
            default_ttl_hours=1,
            cache_dir=temp_cache_dir,
            auto_persist=False,  # Disable auto-persist for testing
        )

    def test_initialization(self, temp_cache_dir):
        """Test cache manager initialization."""
        manager = ResponseCacheManager(
            max_size=10,
            default_ttl_hours=2,
            cache_dir=temp_cache_dir,
            cache_filename="test_cache.json",
            auto_persist=True,
            persist_interval=60,
        )
        
        assert manager.max_size == 10
        assert manager.default_ttl == timedelta(hours=2)
        assert manager.cache_dir == temp_cache_dir
        assert manager.cache_file == temp_cache_dir / "test_cache.json"
        assert manager.auto_persist is True
        assert manager.persist_interval == 60
        assert len(manager._cache) == 0

    def test_initialization_default_cache_dir(self, tmp_path):
        """Test initialization with default cache directory."""
        mock_cache_path = str(tmp_path / "mock_cache")
        
        with patch("create_project.ai.cache_manager.user_cache_dir") as mock_cache_dir:
            mock_cache_dir.return_value = mock_cache_path
            
            manager = ResponseCacheManager()
            expected_dir = Path(mock_cache_path) / "ai"
            assert manager.cache_dir == expected_dir
            assert manager.cache_dir.exists()  # Should have been created

    def test_generate_key(self, cache_manager):
        """Test cache key generation."""
        # Simple parameters
        key1 = cache_manager.generate_key(model="llama2", prompt="test")
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hex digest length
        
        # Same parameters should generate same key
        key2 = cache_manager.generate_key(model="llama2", prompt="test")
        assert key1 == key2
        
        # Different order should generate same key
        key3 = cache_manager.generate_key(prompt="test", model="llama2")
        assert key1 == key3
        
        # Different parameters should generate different key
        key4 = cache_manager.generate_key(model="llama2", prompt="different")
        assert key1 != key4
        
        # Complex parameters
        key5 = cache_manager.generate_key(
            model="llama2",
            messages=[{"role": "user", "content": "test"}],
            options={"temperature": 0.7, "max_tokens": 100},
        )
        assert isinstance(key5, str)
        assert len(key5) == 64

    def test_put_and_get(self, cache_manager):
        """Test basic put and get operations."""
        key = "test_key"
        value = {"response": "test response"}
        
        # Put value in cache
        cache_manager.put(key, value)
        
        # Get value from cache
        retrieved = cache_manager.get(key)
        assert retrieved == value
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats.hits == 1
        assert stats.misses == 0

    def test_get_nonexistent_key(self, cache_manager):
        """Test getting non-existent key."""
        result = cache_manager.get("nonexistent")
        assert result is None
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats.hits == 0
        assert stats.misses == 1

    def test_get_expired_entry(self, cache_manager):
        """Test getting expired entry."""
        key = "expired_key"
        value = "expired_value"
        
        # Put value with very short TTL
        cache_manager.put(key, value, ttl=timedelta(seconds=0.01))
        
        # Wait for expiration
        time.sleep(0.02)
        
        # Try to get expired value
        result = cache_manager.get(key)
        assert result is None
        
        # Check stats
        stats = cache_manager.get_stats()
        assert stats.misses == 1
        assert stats.expired_entries == 1

    def test_put_with_custom_ttl(self, cache_manager):
        """Test putting value with custom TTL."""
        key = "custom_ttl"
        value = "test_value"
        custom_ttl = timedelta(hours=12)
        
        cache_manager.put(key, value, ttl=custom_ttl)
        
        # Check entry exists and has correct expiration
        with cache_manager._lock:
            entry = cache_manager._cache[key]
            expected_expire = entry.created_at + custom_ttl
            assert abs((entry.expires_at - expected_expire).total_seconds()) < 1

    def test_lru_eviction(self, cache_manager):
        """Test LRU eviction when cache is full."""
        # Fill cache to capacity
        for i in range(5):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        assert len(cache_manager._cache) == 5
        
        # Add one more entry, should evict key_0
        cache_manager.put("key_5", "value_5")
        
        assert len(cache_manager._cache) == 5
        assert cache_manager.get("key_0") is None  # Evicted
        assert cache_manager.get("key_5") is not None  # New entry exists
        
        # Check eviction stats
        stats = cache_manager.get_stats()
        assert stats.evictions == 1

    def test_lru_order_update(self, cache_manager):
        """Test that accessing entries updates LRU order."""
        # Fill cache to capacity (5 entries)
        for i in range(5):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        # Access key_0 and key_1 to make them most recently used
        cache_manager.get("key_0")
        cache_manager.get("key_1")
        
        # Add 3 more entries to trigger evictions
        # This should evict key_2, key_3, key_4 (the least recently used)
        for i in range(5, 8):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        # key_0 and key_1 should still exist (were accessed)
        # key_2, key_3, key_4 should be evicted
        assert cache_manager.get("key_0") is not None
        assert cache_manager.get("key_1") is not None
        assert cache_manager.get("key_2") is None
        assert cache_manager.get("key_3") is None
        assert cache_manager.get("key_4") is None

    def test_delete(self, cache_manager):
        """Test deleting cache entries."""
        key = "delete_key"
        cache_manager.put(key, "value")
        
        # Delete existing entry
        result = cache_manager.delete(key)
        assert result is True
        assert cache_manager.get(key) is None
        
        # Delete non-existent entry
        result = cache_manager.delete("nonexistent")
        assert result is False

    def test_clear(self, cache_manager):
        """Test clearing entire cache."""
        # Add some entries
        for i in range(3):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        # Clear cache
        count = cache_manager.clear()
        assert count == 3
        assert len(cache_manager._cache) == 0
        
        # Verify all entries are gone
        for i in range(3):
            assert cache_manager.get(f"key_{i}") is None

    def test_cleanup_expired(self, cache_manager):
        """Test cleaning up expired entries."""
        # Add mix of valid and expired entries
        cache_manager.put("valid_1", "value", ttl=timedelta(hours=1))
        cache_manager.put("expired_1", "value", ttl=timedelta(seconds=0.01))
        cache_manager.put("valid_2", "value", ttl=timedelta(hours=1))
        cache_manager.put("expired_2", "value", ttl=timedelta(seconds=0.01))
        
        # Wait for some to expire
        time.sleep(0.02)
        
        # Clean up expired
        count = cache_manager.cleanup_expired()
        assert count == 2
        assert len(cache_manager._cache) == 2
        assert cache_manager.get("valid_1") is not None
        assert cache_manager.get("valid_2") is not None

    def test_persist_and_load(self, cache_manager):
        """Test persisting cache to disk and loading it back."""
        # Add some entries
        cache_manager.put("key_1", {"data": "value_1"})
        cache_manager.put("key_2", ["value", "list"])
        
        # Persist to disk
        result = cache_manager.persist(force=True)
        assert result is True
        assert cache_manager.cache_file.exists()
        
        # Create new manager to load from disk
        new_manager = ResponseCacheManager(
            max_size=5,
            cache_dir=cache_manager.cache_dir,
            cache_filename=cache_manager.cache_file.name,
            auto_persist=False,
        )
        
        # Check loaded entries
        assert new_manager.get("key_1") == {"data": "value_1"}
        assert new_manager.get("key_2") == ["value", "list"]

    def test_persist_with_error(self, cache_manager):
        """Test persist error handling."""
        cache_manager.put("key", "value")
        
        # Make cache file unwritable
        with patch("pathlib.Path.open", side_effect=PermissionError("No write access")):
            with pytest.raises(CacheError) as exc_info:
                cache_manager.persist(force=True)
            
            assert "Failed to persist cache" in str(exc_info.value)

    def test_load_invalid_cache_file(self, temp_cache_dir):
        """Test loading invalid cache file."""
        # Create invalid JSON file
        cache_file = temp_cache_dir / "invalid.json"
        cache_file.write_text("invalid json{")
        
        # Should not fail, just log error
        manager = ResponseCacheManager(
            cache_dir=temp_cache_dir,
            cache_filename="invalid.json",
        )
        assert len(manager._cache) == 0

    def test_load_cache_with_expired_entries(self, temp_cache_dir):
        """Test loading cache file with expired entries."""
        # Create cache data with mix of valid and expired entries
        now = datetime.now()
        cache_data = {
            "version": "1.0",
            "entries": {
                "valid": {
                    "key": "valid",
                    "value": "valid_data",
                    "created_at": now.isoformat(),
                    "expires_at": (now + timedelta(hours=1)).isoformat(),
                    "access_count": 0,
                    "last_accessed": None,
                },
                "expired": {
                    "key": "expired",
                    "value": "expired_data",
                    "created_at": (now - timedelta(hours=2)).isoformat(),
                    "expires_at": (now - timedelta(hours=1)).isoformat(),
                    "access_count": 0,
                    "last_accessed": None,
                },
            },
        }
        
        cache_file = temp_cache_dir / "mixed.json"
        cache_file.write_text(json.dumps(cache_data))
        
        # Load cache
        manager = ResponseCacheManager(
            cache_dir=temp_cache_dir,
            cache_filename="mixed.json",
        )
        
        # Only valid entry should be loaded
        assert len(manager._cache) == 1
        assert manager.get("valid") == "valid_data"
        assert manager.get("expired") is None

    def test_thread_safety(self, cache_manager):
        """Test thread-safe operations."""
        results = []
        errors = []
        
        def worker(worker_id, iterations=10):
            try:
                for i in range(iterations):
                    key = f"worker_{worker_id}_item_{i}"
                    cache_manager.put(key, f"value_{worker_id}_{i}")
                    
                    # Try to get various keys
                    for j in range(3):
                        test_key = f"worker_{j}_item_{i}"
                        value = cache_manager.get(test_key)
                        if value:
                            results.append((worker_id, test_key, value))
            except Exception as e:
                errors.append((worker_id, str(e)))
        
        # Run multiple threads
        threads = []
        for i in range(5):
            t = Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check no errors occurred
        assert len(errors) == 0
        
        # Check cache size limit is respected
        assert len(cache_manager._cache) <= cache_manager.max_size

    def test_get_cache_info(self, cache_manager):
        """Test getting detailed cache information."""
        # Add some entries
        cache_manager.put("key_1", "value_1")
        cache_manager.put("key_2", {"complex": "value"})
        
        info = cache_manager.get_cache_info()
        
        # Check structure
        assert "config" in info
        assert "stats" in info
        assert "entries" in info
        
        # Check config
        assert info["config"]["max_size"] == 5
        assert info["config"]["default_ttl_hours"] == 1.0
        
        # Check entries
        assert len(info["entries"]) == 2
        entry_info = info["entries"][0]
        assert "key" in entry_info
        assert "created_at" in entry_info
        assert "expires_at" in entry_info
        assert "access_count" in entry_info
        assert "value_type" in entry_info

    def test_auto_persist(self, temp_cache_dir):
        """Test automatic persistence."""
        manager = ResponseCacheManager(
            cache_dir=temp_cache_dir,
            auto_persist=True,
            persist_interval=0.1,  # Very short interval for testing
        )
        
        # Add entry to make cache dirty
        manager.put("key", "value")
        
        # Wait for auto-persist
        time.sleep(0.15)
        
        # Trigger auto-persist check
        manager.put("key2", "value2")
        
        # Check file was created
        assert manager.cache_file.exists()

    def test_estimate_cache_size(self, cache_manager):
        """Test cache size estimation."""
        # Empty cache
        size = cache_manager._estimate_cache_size()
        assert size == 0
        
        # Add some entries
        for i in range(3):
            cache_manager.put(f"key_{i}", f"value_{i}" * 100)
        
        size = cache_manager._estimate_cache_size()
        assert size > 0

    def test_rotate_cache_file(self, cache_manager):
        """Test cache file rotation."""
        # Create cache file
        cache_manager.put("key", "value")
        cache_manager.persist(force=True)
        
        # Create a new cache file to test rotation
        cache_manager.cache_file.write_text('{"test": "data"}')
        
        # Perform rotation
        result = cache_manager.rotate_cache_file(backup_count=3)
        assert result is True
        
        # Check backup file was created
        backup_file = cache_manager.cache_file.with_suffix(".1")
        assert backup_file.exists()
        
        # New cache file should not exist yet (gets created on next persist)
        assert not cache_manager.cache_file.exists()

    def test_rotate_nonexistent_file(self, cache_manager):
        """Test rotating non-existent cache file."""
        result = cache_manager.rotate_cache_file()
        assert result is False

    def test_entry_access_updates(self, cache_manager):
        """Test that getting entries updates access count and time."""
        key = "access_test"
        cache_manager.put(key, "value")
        
        # Initial state
        with cache_manager._lock:
            entry = cache_manager._cache[key]
            assert entry.access_count == 0
            assert entry.last_accessed is None
        
        # Access entry
        cache_manager.get(key)
        
        # Check updated
        with cache_manager._lock:
            entry = cache_manager._cache[key]
            assert entry.access_count == 1
            assert entry.last_accessed is not None

    def test_persist_dirty_flag(self, cache_manager):
        """Test that persist respects dirty flag."""
        # Clean cache should not persist
        result = cache_manager.persist()
        assert result is False
        
        # Make dirty
        cache_manager.put("key", "value")
        assert cache_manager._dirty is True
        
        # Should persist now
        result = cache_manager.persist()
        assert result is True
        assert cache_manager._dirty is False

    def test_complex_value_types(self, cache_manager):
        """Test caching various value types."""
        test_values = [
            ("string", "simple string"),
            ("number", 42),
            ("float", 3.14),
            ("bool", True),
            ("list", [1, 2, 3, "four"]),
            ("dict", {"nested": {"key": "value"}}),
            ("none", None),
        ]
        
        for key, value in test_values:
            cache_manager.put(key, value)
            retrieved = cache_manager.get(key)
            assert retrieved == value

    def test_concurrent_eviction(self, cache_manager):
        """Test concurrent access during eviction."""
        # Fill cache
        for i in range(5):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        def add_entries():
            for i in range(5, 10):
                cache_manager.put(f"key_{i}", f"value_{i}")
        
        def read_entries():
            for _ in range(10):
                for i in range(10):
                    cache_manager.get(f"key_{i}")
        
        # Run concurrent operations
        t1 = Thread(target=add_entries)
        t2 = Thread(target=read_entries)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Cache should still respect size limit
        assert len(cache_manager._cache) <= cache_manager.max_size