# ABOUTME: Comprehensive tests for AI response cache system with LRU and TTL validation
# ABOUTME: Tests thread safety, persistence, eviction policies, and cache statistics

import pytest
import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, Mock
from tempfile import TemporaryDirectory

from create_project.ai.cache_manager import (
    ResponseCacheManager,
    CacheEntry,
    CacheStats,
)
from create_project.ai.exceptions import CacheError


class TestCacheEntry:
    """Test suite for CacheEntry dataclass."""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation with required fields."""
        now = datetime.now()
        expires = now + timedelta(hours=1)
        
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            created_at=now,
            expires_at=expires
        )
        
        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.created_at == now
        assert entry.expires_at == expires
        assert entry.access_count == 0
        assert entry.last_accessed is None
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration checking."""
        now = datetime.now()
        
        # Valid entry (expires in future)
        valid_entry = CacheEntry(
            key="valid",
            value="data",
            created_at=now,
            expires_at=now + timedelta(seconds=10)
        )
        
        # Expired entry (expires in past)
        expired_entry = CacheEntry(
            key="expired",
            value="data",
            created_at=now - timedelta(hours=2),
            expires_at=now - timedelta(hours=1)
        )
        
        assert valid_entry.is_valid() is True
        assert valid_entry.is_expired() is False
        
        assert expired_entry.is_valid() is False
        assert expired_entry.is_expired() is True
    
    def test_cache_entry_access_tracking(self):
        """Test access tracking functionality."""
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert entry.access_count == 0
        assert entry.last_accessed is None
        
        entry.access()
        
        assert entry.access_count == 1
        assert entry.last_accessed is not None
        
        entry.access()
        
        assert entry.access_count == 2


class TestCacheStats:
    """Test suite for CacheStats dataclass."""
    
    def test_cache_stats_creation(self):
        """Test cache stats creation with default values."""
        stats = CacheStats()
        
        assert stats.total_entries == 0
        assert stats.max_size == 0
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.expired_entries == 0
        assert stats.total_size_bytes == 0
        assert stats.cache_file_size == 0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        stats = CacheStats(hits=75, misses=25)
        assert stats.hit_rate == 75.0
        
        stats = CacheStats(hits=0, misses=0)
        assert stats.hit_rate == 0.0
        
        stats = CacheStats(hits=50, misses=50)
        assert stats.hit_rate == 50.0
    
    def test_fill_rate_calculation(self):
        """Test cache fill rate calculation."""
        stats = CacheStats(total_entries=75, max_size=100)
        assert stats.fill_rate == 75.0
        
        stats = CacheStats(total_entries=0, max_size=100)
        assert stats.fill_rate == 0.0
        
        stats = CacheStats(total_entries=10, max_size=0)
        assert stats.fill_rate == 0.0


class TestResponseCacheManager:
    """Test suite for ResponseCacheManager class."""
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory for cache files."""
        with TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_dir):
        """ResponseCacheManager instance with temporary directory."""
        return ResponseCacheManager(
            max_size=5,
            default_ttl_hours=1,
            cache_dir=temp_dir,
            auto_persist=False  # Disable auto-persist for tests
        )
    
    def test_initialization_default(self):
        """Test cache manager initialization with defaults."""
        with TemporaryDirectory() as temp_dir:
            cache = ResponseCacheManager(cache_dir=Path(temp_dir))
            
            assert cache.max_size == 100
            assert cache.default_ttl == timedelta(hours=24)
            assert cache.cache_dir == Path(temp_dir)
            assert cache.auto_persist is True
            assert cache.persist_interval == 300
    
    def test_initialization_custom(self, temp_dir):
        """Test cache manager initialization with custom values."""
        cache = ResponseCacheManager(
            max_size=50,
            default_ttl_hours=12,
            cache_dir=temp_dir,
            cache_filename="custom.json",
            auto_persist=False,
            persist_interval=600
        )
        
        assert cache.max_size == 50
        assert cache.default_ttl == timedelta(hours=12)
        assert cache.cache_file.name == "custom.json"
        assert cache.auto_persist is False
        assert cache.persist_interval == 600
    
    def test_generate_key_basic(self, cache_manager):
        """Test cache key generation from parameters."""
        key1 = cache_manager.generate_key(prompt="hello", model="llama")
        key2 = cache_manager.generate_key(prompt="hello", model="llama")
        key3 = cache_manager.generate_key(prompt="world", model="llama")
        
        assert isinstance(key1, str)
        assert len(key1) == 64  # SHA-256 hex length
        assert key1 == key2  # Same inputs = same key
        assert key1 != key3  # Different inputs = different keys
    
    def test_generate_key_complex_params(self, cache_manager):
        """Test key generation with complex parameters."""
        key1 = cache_manager.generate_key(
            prompt="test",
            config={"temp": 0.7, "tokens": 100},
            messages=[{"role": "user", "content": "hello"}]
        )
        
        key2 = cache_manager.generate_key(
            prompt="test",
            config={"tokens": 100, "temp": 0.7},  # Different order
            messages=[{"role": "user", "content": "hello"}]
        )
        
        assert key1 == key2  # Should be same despite parameter order
    
    def test_put_and_get_basic(self, cache_manager):
        """Test basic cache put and get operations."""
        key = "test_key"
        value = "test_value"
        
        # Initially empty
        assert cache_manager.get(key) is None
        
        # Put value
        cache_manager.put(key, value)
        
        # Retrieve value
        retrieved = cache_manager.get(key)
        assert retrieved == value
    
    def test_put_and_get_with_ttl(self, cache_manager):
        """Test cache operations with custom TTL."""
        key = "test_key"
        value = "test_value"
        short_ttl = timedelta(milliseconds=10)
        
        cache_manager.put(key, value, ttl=short_ttl)
        
        # Should be available immediately
        assert cache_manager.get(key) == value
        
        # Wait for expiration
        time.sleep(0.02)  # 20ms
        
        # Should be expired now
        assert cache_manager.get(key) is None
    
    def test_put_overwrites_existing(self, cache_manager):
        """Test that put overwrites existing entries."""
        key = "test_key"
        old_value = "old_value"
        new_value = "new_value"
        
        cache_manager.put(key, old_value)
        assert cache_manager.get(key) == old_value
        
        cache_manager.put(key, new_value)
        assert cache_manager.get(key) == new_value
    
    def test_delete_entry(self, cache_manager):
        """Test cache entry deletion."""
        key = "test_key"
        value = "test_value"
        
        cache_manager.put(key, value)
        assert cache_manager.get(key) == value
        
        # Delete existing entry
        deleted = cache_manager.delete(key)
        assert deleted is True
        assert cache_manager.get(key) is None
        
        # Delete non-existent entry
        deleted = cache_manager.delete("nonexistent")
        assert deleted is False
    
    def test_clear_cache(self, cache_manager):
        """Test clearing entire cache."""
        # Add multiple entries
        for i in range(3):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        # Verify entries exist
        for i in range(3):
            assert cache_manager.get(f"key_{i}") == f"value_{i}"
        
        # Clear cache
        cleared_count = cache_manager.clear()
        assert cleared_count == 3
        
        # Verify cache is empty
        for i in range(3):
            assert cache_manager.get(f"key_{i}") is None
    
    def test_lru_eviction(self, cache_manager):
        """Test LRU eviction when cache is full."""
        # Fill cache to max size (5)
        for i in range(5):
            cache_manager.put(f"key_{i}", f"value_{i}")
        
        # All entries should be present
        for i in range(5):
            assert cache_manager.get(f"key_{i}") == f"value_{i}"
        
        # Access key_1 to make it more recently used
        cache_manager.get("key_1")
        
        # Add one more entry (should evict key_0, the least recently used)
        cache_manager.put("key_new", "value_new")
        
        # key_0 should be evicted
        assert cache_manager.get("key_0") is None
        
        # key_1 should still be present (was accessed recently)
        assert cache_manager.get("key_1") == "value_1"
        
        # New entry should be present
        assert cache_manager.get("key_new") == "value_new"
    
    def test_cleanup_expired_entries(self, cache_manager):
        """Test cleanup of expired entries."""
        now = datetime.now()
        
        # Add expired entry
        cache_manager.put("expired_key", "value", ttl=timedelta(milliseconds=1))
        
        # Add valid entry
        cache_manager.put("valid_key", "value", ttl=timedelta(hours=1))
        
        # Wait for expiration
        time.sleep(0.01)
        
        # Run cleanup
        expired_count = cache_manager.cleanup_expired()
        
        assert expired_count == 1
        assert cache_manager.get("expired_key") is None
        assert cache_manager.get("valid_key") == "value"
    
    def test_cache_statistics(self, cache_manager):
        """Test cache statistics tracking."""
        # Initial stats
        stats = cache_manager.get_stats()
        assert stats.total_entries == 0
        assert stats.hits == 0
        assert stats.misses == 0
        
        # Add entry and access it
        cache_manager.put("key1", "value1")
        assert cache_manager.get("key1") == "value1"  # Hit
        assert cache_manager.get("nonexistent") is None  # Miss
        
        # Check updated stats
        stats = cache_manager.get_stats()
        assert stats.total_entries == 1
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 50.0
    
    def test_persistence_save_and_load(self, cache_manager, temp_dir):
        """Test cache persistence to disk."""
        # Add entries
        cache_manager.put("key1", "value1")
        cache_manager.put("key2", {"nested": "data"})
        
        # Persist cache
        cache_manager.persist(force=True)
        
        # Verify cache file exists
        assert cache_manager.cache_file.exists()
        
        # Create new cache manager with same directory
        new_cache = ResponseCacheManager(
            max_size=5,
            cache_dir=temp_dir,
            auto_persist=False
        )
        
        # Verify data was loaded
        assert new_cache.get("key1") == "value1"
        assert new_cache.get("key2") == {"nested": "data"}
    
    def test_persistence_expired_entries_not_loaded(self, cache_manager, temp_dir):
        """Test that expired entries are not loaded from disk."""
        # Add entry with very short TTL
        cache_manager.put("expired_key", "value", ttl=timedelta(milliseconds=1))
        cache_manager.put("valid_key", "value", ttl=timedelta(hours=1))
        
        # Persist immediately
        cache_manager.persist(force=True)
        
        # Wait for expiration
        time.sleep(0.01)
        
        # Create new cache manager
        new_cache = ResponseCacheManager(
            max_size=5,
            cache_dir=temp_dir,
            auto_persist=False
        )
        
        # Only valid entry should be loaded
        assert new_cache.get("expired_key") is None
        assert new_cache.get("valid_key") == "value"
    
    def test_persistence_error_handling(self, cache_manager):
        """Test error handling during persistence."""
        cache_manager.put("key", "value")
        
        # Mock file operations to raise an exception
        with patch('pathlib.Path.open', side_effect=PermissionError("Mock error")):
            with pytest.raises(CacheError):
                cache_manager.persist(force=True)
    
    def test_get_cache_info(self, cache_manager):
        """Test getting detailed cache information."""
        # Add entries
        cache_manager.put("key1", "short_value")
        cache_manager.put("key2", "longer_value_here", ttl=timedelta(minutes=30))
        
        # Access one entry
        cache_manager.get("key1")
        
        info = cache_manager.get_cache_info()
        
        # Check structure
        assert "config" in info
        assert "stats" in info
        assert "entries" in info
        
        # Check config
        assert info["config"]["max_size"] == 5
        assert info["config"]["default_ttl_hours"] == 1
        
        # Check entries
        assert len(info["entries"]) == 2
        
        # Find entry info
        entry1_info = next(e for e in info["entries"] if e["key"].startswith("key1"))
        assert entry1_info["access_count"] == 1
        assert entry1_info["value_type"] == "str"
        assert entry1_info["is_expired"] is False
    
    def test_thread_safety(self, cache_manager):
        """Test thread-safe operations."""
        results = []
        error_list = []
        
        def cache_worker(worker_id):
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    value = f"worker_{worker_id}_value_{i}"
                    
                    cache_manager.put(key, value)
                    retrieved = cache_manager.get(key)
                    
                    if retrieved != value:
                        error_list.append(f"Worker {worker_id}: Expected {value}, got {retrieved}")
                    
                    results.append((worker_id, i, retrieved == value))
            except Exception as e:
                error_list.append(f"Worker {worker_id} error: {e}")
        
        # Start multiple threads
        threads = []
        for worker_id in range(3):
            thread = threading.Thread(target=cache_worker, args=(worker_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(error_list) == 0, f"Thread safety errors: {error_list}"
        assert len(results) == 30  # 3 workers * 10 operations
        assert all(success for _, _, success in results)
    
    def test_cache_file_rotation(self, cache_manager):
        """Test cache file rotation functionality."""
        # Create original cache file
        cache_manager.put("key", "value")
        cache_manager.persist(force=True)
        
        # Verify file exists
        assert cache_manager.cache_file.exists()
        original_content = cache_manager.cache_file.read_text()
        
        # Rotate cache file
        rotated = cache_manager.rotate_cache_file(backup_count=3)
        assert rotated is True
        
        # Check that backup was created
        backup_file = cache_manager.cache_file.with_suffix(".1")
        assert backup_file.exists()
        assert backup_file.read_text() == original_content
        
        # Original file should be gone
        assert not cache_manager.cache_file.exists()
    
    def test_auto_persist_interval(self, temp_dir):
        """Test auto-persistence with time interval."""
        cache = ResponseCacheManager(
            max_size=5,
            cache_dir=temp_dir,
            auto_persist=True,
            persist_interval=1  # 1 second
        )
        
        cache.put("key1", "value1")
        
        # Should not persist immediately
        assert not cache.cache_file.exists()
        
        # Simulate time passing by directly manipulating the internal timestamp
        cache._last_persist_time = time.time() - 2  # 2 seconds ago
        
        cache.put("key2", "value2")
        
        # Now should have persisted
        assert cache.cache_file.exists()
    
    def test_large_cache_size_estimation(self, cache_manager):
        """Test cache size estimation with various data types."""
        # Add different types of data
        cache_manager.put("string", "simple string value")
        cache_manager.put("dict", {"key": "value", "nested": {"data": [1, 2, 3]}})
        cache_manager.put("list", [1, 2, 3, "four", {"five": 6}])
        cache_manager.put("number", 42)
        cache_manager.put("boolean", True)
        
        stats = cache_manager.get_stats()
        
        # Size should be estimated (not zero)
        assert stats.total_size_bytes > 0
        assert stats.total_entries == 5
    
    def test_cache_key_collision_resistance(self, cache_manager):
        """Test that similar parameters generate different keys."""
        # Similar but different parameters
        key1 = cache_manager.generate_key(a="hello", b="world")
        key2 = cache_manager.generate_key(a="hell", b="oworld")
        key3 = cache_manager.generate_key(ab="hello", b="world")
        
        # All keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3
    
    def test_cache_with_none_values(self, cache_manager):
        """Test caching None values."""
        cache_manager.put("none_key", None)
        
        # Should be able to retrieve None
        assert cache_manager.get("none_key") is None
        
        # But should differentiate from missing keys via internal state
        assert "none_key" in cache_manager._cache
        assert "missing_key" not in cache_manager._cache