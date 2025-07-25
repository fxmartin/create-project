# ABOUTME: Unit tests for AI exceptions module - comprehensive exception class testing
# ABOUTME: Tests exception hierarchy, initialization, attributes, and inheritance structure

"""
Unit tests for create_project.ai.exceptions module.

Tests all AI-specific exception classes including their initialization,
attribute handling, inheritance structure, and error message formatting.
"""

import pytest

from create_project.ai.exceptions import (
    AIError,
    CacheError,
    ContextCollectionError,
    ModelNotAvailableError,
    OllamaNotFoundError,
    ResponseTimeoutError,
)
from create_project.core.exceptions import ProjectGenerationError


class TestAIError:
    """Test the base AIError exception class."""

    def test_ai_error_basic_initialization(self):
        """Test basic AIError initialization."""
        error = AIError("Test error message")

        assert str(error) == "Test error message"
        assert error.original_error is None
        assert isinstance(error, ProjectGenerationError)

    def test_ai_error_with_original_error(self):
        """Test AIError initialization with original error."""
        original = ValueError("Original error")
        error = AIError("Test error message", original_error=original)

        assert str(error) == "Test error message"
        assert error.original_error is original
        assert isinstance(error.original_error, ValueError)

    def test_ai_error_inheritance(self):
        """Test AIError inheritance hierarchy."""
        error = AIError("Test message")

        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)
        assert isinstance(error, Exception)

    def test_ai_error_attributes(self):
        """Test AIError attribute access."""
        original = RuntimeError("Runtime issue")
        error = AIError("Main error", original_error=original)

        # Test direct attribute access
        assert hasattr(error, "original_error")
        assert error.original_error is original

        # Test that it's still a proper exception
        assert hasattr(error, "args")
        assert error.args == ("Main error",)


class TestOllamaNotFoundError:
    """Test the OllamaNotFoundError exception class."""

    def test_ollama_not_found_default_message(self):
        """Test OllamaNotFoundError with default message."""
        error = OllamaNotFoundError()

        assert "Ollama not found or not running" in str(error)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)

    def test_ollama_not_found_custom_message(self):
        """Test OllamaNotFoundError with custom message."""
        custom_message = "Ollama service is not available on port 11434"
        error = OllamaNotFoundError(custom_message)

        assert str(error) == custom_message
        assert isinstance(error, AIError)

    def test_ollama_not_found_inheritance(self):
        """Test OllamaNotFoundError inheritance chain."""
        error = OllamaNotFoundError()

        assert isinstance(error, OllamaNotFoundError)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)
        assert isinstance(error, Exception)

    def test_ollama_not_found_original_error_none(self):
        """Test that OllamaNotFoundError has no original error by default."""
        error = OllamaNotFoundError()

        assert error.original_error is None


class TestModelNotAvailableError:
    """Test the ModelNotAvailableError exception class."""

    def test_model_not_available_basic(self):
        """Test ModelNotAvailableError with just model name."""
        error = ModelNotAvailableError("llama2")

        assert "Model 'llama2' not available" in str(error)
        assert error.model_name == "llama2"
        assert error.available_models == []
        assert isinstance(error, AIError)

    def test_model_not_available_with_available_models(self):
        """Test ModelNotAvailableError with available models list."""
        available = ["gpt-3.5-turbo", "llama3", "mistral"]
        error = ModelNotAvailableError("nonexistent-model", available_models=available)

        error_message = str(error)
        assert "Model 'nonexistent-model' not available" in error_message
        assert "Available models:" in error_message
        assert "gpt-3.5-turbo" in error_message
        assert "llama3" in error_message
        assert "mistral" in error_message

        assert error.model_name == "nonexistent-model"
        assert error.available_models == available

    def test_model_not_available_empty_available_models(self):
        """Test ModelNotAvailableError with empty available models list."""
        error = ModelNotAvailableError("test-model", available_models=[])

        assert "Model 'test-model' not available" in str(error)
        assert "Available models:" not in str(error)
        assert error.model_name == "test-model"
        assert error.available_models == []

    def test_model_not_available_attributes(self):
        """Test ModelNotAvailableError attribute access."""
        available = ["model1", "model2"]
        error = ModelNotAvailableError("missing-model", available_models=available)

        assert hasattr(error, "model_name")
        assert hasattr(error, "available_models")
        assert error.model_name == "missing-model"
        assert error.available_models == available

    def test_model_not_available_inheritance(self):
        """Test ModelNotAvailableError inheritance."""
        error = ModelNotAvailableError("test-model")

        assert isinstance(error, ModelNotAvailableError)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)


class TestResponseTimeoutError:
    """Test the ResponseTimeoutError exception class."""

    def test_response_timeout_initialization(self):
        """Test ResponseTimeoutError initialization."""
        error = ResponseTimeoutError(30)

        assert "AI response timeout after 30 seconds" in str(error)
        assert error.timeout == 30
        assert isinstance(error, AIError)

    def test_response_timeout_different_values(self):
        """Test ResponseTimeoutError with different timeout values."""
        test_cases = [5, 10, 60, 120, 300]

        for timeout in test_cases:
            error = ResponseTimeoutError(timeout)

            assert f"timeout after {timeout} seconds" in str(error)
            assert error.timeout == timeout

    def test_response_timeout_attributes(self):
        """Test ResponseTimeoutError attribute access."""
        error = ResponseTimeoutError(45)

        assert hasattr(error, "timeout")
        assert error.timeout == 45
        assert isinstance(error.timeout, int)

    def test_response_timeout_inheritance(self):
        """Test ResponseTimeoutError inheritance."""
        error = ResponseTimeoutError(30)

        assert isinstance(error, ResponseTimeoutError)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)


class TestCacheError:
    """Test the CacheError exception class."""

    def test_cache_error_basic(self):
        """Test CacheError with basic message."""
        error = CacheError("Cache operation failed")

        assert str(error) == "Cache operation failed"
        assert error.cache_operation is None
        assert isinstance(error, AIError)

    def test_cache_error_with_operation(self):
        """Test CacheError with cache operation specified."""
        error = CacheError("Failed to store cache entry", cache_operation="store")

        assert str(error) == "Failed to store cache entry"
        assert error.cache_operation == "store"

    def test_cache_error_different_operations(self):
        """Test CacheError with different cache operations."""
        operations = ["get", "set", "delete", "clear", "expire"]

        for operation in operations:
            error = CacheError(f"Cache {operation} failed", cache_operation=operation)

            assert error.cache_operation == operation
            assert f"Cache {operation} failed" in str(error)

    def test_cache_error_attributes(self):
        """Test CacheError attribute access."""
        error = CacheError("Cache error", cache_operation="retrieve")

        assert hasattr(error, "cache_operation")
        assert error.cache_operation == "retrieve"

    def test_cache_error_inheritance(self):
        """Test CacheError inheritance."""
        error = CacheError("Test message")

        assert isinstance(error, CacheError)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)


class TestContextCollectionError:
    """Test the ContextCollectionError exception class."""

    def test_context_collection_error_basic(self):
        """Test ContextCollectionError with basic message."""
        error = ContextCollectionError("Failed to collect context")

        assert str(error) == "Failed to collect context"
        assert error.details == {}
        assert error.original_error is None
        assert isinstance(error, AIError)

    def test_context_collection_error_with_details(self):
        """Test ContextCollectionError with details."""
        details = {"file_path": "/test/file.py", "line_number": 42}
        error = ContextCollectionError("Context collection failed", details=details)

        assert str(error) == "Context collection failed"
        assert error.details == details
        assert error.original_error is None

    def test_context_collection_error_with_original_error(self):
        """Test ContextCollectionError with original error."""
        original = FileNotFoundError("File not found")
        error = ContextCollectionError(
            "Failed to read file for context",
            original_error=original
        )

        assert str(error) == "Failed to read file for context"
        assert error.original_error is original
        assert error.details == {}

    def test_context_collection_error_full_initialization(self):
        """Test ContextCollectionError with all parameters."""
        details = {"module": "test_module", "function": "test_function"}
        original = RuntimeError("Runtime issue")
        error = ContextCollectionError(
            "Complete context collection failure",
            details=details,
            original_error=original
        )

        assert str(error) == "Complete context collection failure"
        assert error.details == details
        assert error.original_error is original

    def test_context_collection_error_none_details(self):
        """Test ContextCollectionError with None details."""
        error = ContextCollectionError("Test message", details=None)

        assert error.details == {}  # Should default to empty dict

    def test_context_collection_error_attributes(self):
        """Test ContextCollectionError attribute access."""
        details = {"key": "value"}
        original = ValueError("Test error")
        error = ContextCollectionError("Message", details=details, original_error=original)

        assert hasattr(error, "details")
        assert hasattr(error, "original_error")
        assert error.details == details
        assert error.original_error is original

    def test_context_collection_error_inheritance(self):
        """Test ContextCollectionError inheritance."""
        error = ContextCollectionError("Test message")

        assert isinstance(error, ContextCollectionError)
        assert isinstance(error, AIError)
        assert isinstance(error, ProjectGenerationError)


class TestExceptionInteraction:
    """Test interactions between different exception types."""

    def test_all_exceptions_are_ai_errors(self):
        """Test that all AI exceptions inherit from AIError."""
        exceptions = [
            OllamaNotFoundError(),
            ModelNotAvailableError("test"),
            ResponseTimeoutError(30),
            CacheError("test"),
            ContextCollectionError("test"),
        ]

        for exception in exceptions:
            assert isinstance(exception, AIError)
            assert isinstance(exception, ProjectGenerationError)

    def test_exception_chaining(self):
        """Test exception chaining with original errors."""
        original = ValueError("Original error")

        # Test AIError chaining
        ai_error = AIError("AI error", original_error=original)
        assert ai_error.original_error is original

        # Test ContextCollectionError chaining
        context_error = ContextCollectionError("Context error", original_error=original)
        assert context_error.original_error is original

    def test_exception_catching(self):
        """Test catching exceptions by base type."""
        exceptions = [
            OllamaNotFoundError(),
            ModelNotAvailableError("test"),
            ResponseTimeoutError(30),
            CacheError("test"),
            ContextCollectionError("test"),
        ]

        for exception in exceptions:
            # All should be catchable as AIError
            try:
                raise exception
            except AIError as e:
                assert e is exception

            # All should be catchable as ProjectGenerationError
            try:
                raise exception
            except ProjectGenerationError as e:
                assert e is exception

    def test_exception_message_formats(self):
        """Test that all exception message formats are reasonable."""
        exceptions_and_checks = [
            (OllamaNotFoundError(), lambda msg: "Ollama" in msg),
            (ModelNotAvailableError("test"), lambda msg: "Model" in msg and "test" in msg),
            (ResponseTimeoutError(30), lambda msg: "timeout" in msg and "30" in msg),
            (CacheError("Cache failed"), lambda msg: "Cache failed" in msg),
            (ContextCollectionError("Context failed"), lambda msg: "Context failed" in msg),
        ]

        for exception, check_func in exceptions_and_checks:
            message = str(exception)
            assert isinstance(message, str)
            assert len(message) > 0
            assert check_func(message)


class TestExceptionRaising:
    """Test raising and handling exceptions in realistic scenarios."""

    def test_raise_and_catch_ollama_not_found(self):
        """Test raising and catching OllamaNotFoundError."""
        with pytest.raises(OllamaNotFoundError) as exc_info:
            raise OllamaNotFoundError("Ollama service unavailable")

        assert "Ollama service unavailable" in str(exc_info.value)
        assert isinstance(exc_info.value, AIError)

    def test_raise_and_catch_model_not_available(self):
        """Test raising and catching ModelNotAvailableError."""
        with pytest.raises(ModelNotAvailableError) as exc_info:
            raise ModelNotAvailableError("gpt-4", available_models=["gpt-3.5", "llama2"])

        error = exc_info.value
        assert error.model_name == "gpt-4"
        assert "gpt-3.5" in str(error)
        assert "llama2" in str(error)

    def test_raise_and_catch_timeout_error(self):
        """Test raising and catching ResponseTimeoutError."""
        with pytest.raises(ResponseTimeoutError) as exc_info:
            raise ResponseTimeoutError(60)

        error = exc_info.value
        assert error.timeout == 60
        assert "60 seconds" in str(error)

    def test_raise_and_catch_as_base_type(self):
        """Test catching specific exceptions as base AIError."""
        specific_exceptions = [
            OllamaNotFoundError("Test"),
            ModelNotAvailableError("test-model"),
            ResponseTimeoutError(30),
            CacheError("Cache issue"),
            ContextCollectionError("Context issue"),
        ]

        for specific_exception in specific_exceptions:
            with pytest.raises(AIError):
                raise specific_exception
