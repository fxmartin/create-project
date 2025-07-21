# ABOUTME: AI module for Ollama integration providing intelligent assistance
# ABOUTME: Exports main AI service and exception classes for external consumption

from .cache_manager import (
    CacheEntry,
    CacheStats,
    ResponseCacheManager,
)
from .exceptions import (
    AIError,
    CacheError,
    ModelNotAvailableError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from .prompt_manager import PromptManager
from .response_generator import (
    GenerationConfig,
    ResponseGenerator,
    ResponseQuality,
)
from .types import PromptType

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
    "PromptManager",
]
