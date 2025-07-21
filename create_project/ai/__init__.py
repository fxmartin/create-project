# ABOUTME: AI module for Ollama integration providing intelligent project creation assistance
# ABOUTME: Exports main AI service and exception classes for external consumption

from .exceptions import (
    AIError,
    OllamaNotFoundError,
    ModelNotAvailableError,
    ResponseTimeoutError,
    CacheError,
)
from .response_generator import (
    ResponseGenerator,
    PromptType,
    GenerationConfig,
    ResponseQuality,
)
from .cache_manager import (
    ResponseCacheManager,
    CacheEntry,
    CacheStats,
)

__all__ = [
    "AIError",
    "OllamaNotFoundError", 
    "ModelNotAvailableError",
    "ResponseTimeoutError",
    "CacheError",
    "ResponseGenerator",
    "PromptType",
    "GenerationConfig",
    "ResponseQuality",
    "ResponseCacheManager",
    "CacheEntry",
    "CacheStats",
]