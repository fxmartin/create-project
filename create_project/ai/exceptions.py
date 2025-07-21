# ABOUTME: AI-specific exceptions for Ollama integration and caching errors
# ABOUTME: Hierarchical exception system inheriting from base project exceptions

"""Exception hierarchy for AI module operations.

This module defines specific exceptions for AI-related errors that can occur
during Ollama integration and AI assistance operations. All exceptions inherit
from the base ProjectGenerationError to maintain consistency with the project's
error handling architecture.

Exception Hierarchy:
    ProjectGenerationError (base)
    ├── AIError
    │   ├── OllamaNotFoundError - Ollama binary/service not available
    │   ├── ModelNotAvailableError - Requested model not found
    │   ├── ResponseGenerationError - AI response generation failed
    │   │   └── ResponseTimeoutError - AI response timed out
    │   └── CacheError - Cache operation failed
    └── AIAssistanceError - AI help generation failed

Example:
    try:
        response = await ai_service.get_help(error_context)
    except OllamaNotFoundError:
        # Fall back to static help
        return get_static_help()
    except ResponseTimeoutError:
        # Try with shorter timeout or simpler prompt
        return await ai_service.get_quick_help(error_context)
"""

from typing import Optional

from create_project.core.exceptions import ProjectGenerationError


class AIError(ProjectGenerationError):
    """Base exception for AI-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class OllamaNotFoundError(AIError):
    """Raised when Ollama is not installed or not accessible."""

    def __init__(self, message: str = "Ollama not found or not running"):
        super().__init__(message)


class ModelNotAvailableError(AIError):
    """Raised when requested model is not available in Ollama."""

    def __init__(self, model_name: str, available_models: Optional[list] = None):
        message = f"Model '{model_name}' not available"
        if available_models:
            message += f". Available models: {', '.join(available_models)}"
        super().__init__(message)
        self.model_name = model_name
        self.available_models = available_models or []


class ResponseTimeoutError(AIError):
    """Raised when AI response takes too long."""

    def __init__(self, timeout: int):
        super().__init__(f"AI response timeout after {timeout} seconds")
        self.timeout = timeout


class CacheError(AIError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, cache_operation: Optional[str] = None):
        super().__init__(message)
        self.cache_operation = cache_operation


class ContextCollectionError(AIError):
    """Raised when error context collection fails."""

    def __init__(self, message: str, details: Optional[dict] = None, original_error: Optional[Exception] = None):
        super().__init__(message, original_error)
        self.details = details or {}
