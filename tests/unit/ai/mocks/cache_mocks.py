# ABOUTME: Mock implementations for cache manager testing
# ABOUTME: Provides controllable cache behavior for various test scenarios

"""Cache manager mock implementations."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class MockCacheManager:
    """Mock implementation of ResponseCacheManager."""
    
    def __init__(
        self,
        cache_enabled: bool = True,
        always_miss: bool = False,
        always_expired: bool = False,
        raise_on_get: bool = False,
        raise_on_set: bool = False,
    ):
        """Initialize mock cache manager."""
        self.cache_enabled = cache_enabled
        self.always_miss = always_miss
        self.always_expired = always_expired
        self.raise_on_get = raise_on_get
        self.raise_on_set = raise_on_set
        
        # Internal state tracking
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.get_count = 0
        self.set_count = 0
        self.hit_count = 0
        self.miss_count = 0
        self.clear_count = 0
        self.persist_count = 0
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Mock get method."""
        self.get_count += 1
        
        if not self.cache_enabled:
            self.miss_count += 1
            return None
        
        if self.raise_on_get:
            raise RuntimeError("Mock cache get error")
        
        if self.always_miss:
            self.miss_count += 1
            return None
        
        if key in self.cache:
            entry = self.cache[key]
            
            if self.always_expired:
                self.miss_count += 1
                return None
            
            # Check expiration
            if "expires_at" in entry:
                if datetime.now() > entry["expires_at"]:
                    self.miss_count += 1
                    return None
            
            self.hit_count += 1
            return entry.get("value")
        
        self.miss_count += 1
        return None
    
    def set(self, key: str, value: Dict[str, Any], ttl_hours: Optional[int] = 24) -> None:
        """Mock set method."""
        self.set_count += 1
        
        if not self.cache_enabled:
            return
        
        if self.raise_on_set:
            raise RuntimeError("Mock cache set error")
        
        expires_at = datetime.now() + timedelta(hours=ttl_hours) if ttl_hours else None
        
        self.cache[key] = {
            "value": value,
            "expires_at": expires_at,
            "created_at": datetime.now(),
        }
    
    def clear(self) -> None:
        """Mock clear method."""
        self.clear_count += 1
        self.cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self.cache),
            "hits": self.hit_count,
            "misses": self.miss_count,
            "hit_rate": self.hit_count / (self.hit_count + self.miss_count) if (self.hit_count + self.miss_count) > 0 else 0,
            "get_count": self.get_count,
            "set_count": self.set_count,
            "clear_count": self.clear_count,
        }
    
    def contains(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self.cache
    
    def size(self) -> int:
        """Get cache size."""
        return len(self.cache)
    
    def persist(self) -> None:
        """Mock persist method."""
        self.persist_count += 1
    
    def generate_key(self, **kwargs) -> str:
        """Generate cache key from parameters."""
        # Simple key generation for testing
        key_parts = []
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        return ":".join(key_parts)
    
    def put(self, key: str, value: Any) -> None:
        """Alias for set method (used by AIService)."""
        self.set(key, value)