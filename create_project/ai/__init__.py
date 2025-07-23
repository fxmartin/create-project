# ABOUTME: AI module for Ollama integration providing intelligent assistance
# ABOUTME: Exports main AI service and exception classes for external consumption

"""AI module for intelligent project creation assistance using Ollama.

This module provides comprehensive AI integration for the create-project
application, enabling intelligent assistance through Ollama models. It includes
response generation, caching, model management, and error context collection.

Key Components:
    - Response Generation: AI-powered help, suggestions, and explanations
    - Model Management: Discovery and selection of appropriate Ollama models
    - Response Caching: LRU cache with TTL for improved performance
    - Prompt Management: Template-based prompt generation with validation
    - Error Context: Intelligent error context collection with PII sanitization

Main Exports:
    - ResponseGenerator: Main class for AI response generation
    - PromptType: Enum for different prompt types (error_help, suggestions, etc.)
    - GenerationConfig: Configuration for response generation
    - ResponseCacheManager: LRU cache manager for AI responses
    - PromptManager: Template-based prompt management
    - Various exception classes for error handling

Usage Example:
    ```python
    from create_project.ai import (
        ResponseGenerator,
        GenerationConfig,
        PromptType,
        ResponseCacheManager
    )
    import asyncio

    async def main():
        # Initialize components
        generator = ResponseGenerator()
        cache = ResponseCacheManager(max_size=100)

        # Configure generation
        config = GenerationConfig(
            model_preference="llama2:7b",
            temperature=0.7,
            max_tokens=1000,
            quality_check=True
        )

        # Generate error help
        context = {
            "error_message": "Permission denied",
            "error_type": "PermissionError",
            "operation": "Creating directory"
        }

        # Check cache first
        cache_key = cache.generate_key(
            prompt_type=PromptType.ERROR_HELP.value,
            **context
        )

        cached = cache.get(cache_key)
        if cached:
            print("Using cached response:", cached)
        else:
            # Generate new response
            response = await generator.generate_response(
                PromptType.ERROR_HELP,
                context,
                config
            )

            # Cache the response
            cache.put(cache_key, response)
            print("Generated response:", response)

    asyncio.run(main())
    ```

The AI module is designed to gracefully degrade when Ollama is unavailable,
providing fallback responses to ensure the application remains functional.
All AI features are optional enhancements to the core functionality.
"""

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
